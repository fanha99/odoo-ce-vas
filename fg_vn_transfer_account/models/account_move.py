from odoo import api, models
from odoo.tools import SQL

# Among linked entries of the same day, bank entries come first, then cash ones.
JOURNAL_PRIORITY = {'bank': 0, 'cash': 1}
OTHER_JOURNAL_PRIORITY = 2


class AccountMove(models.Model):
    _inherit = 'account.move'

    # -------------------------------------------------------------------------
    # LINKS THROUGH HIDDEN TRANSFER ACCOUNTS
    # -------------------------------------------------------------------------
    #
    # A cash deposit is two entries meeting on a transfer account:
    #     CASH/001  Dr 113 / Cr 1111        BANK/001  Dr 1121 / Cr 113
    # When the company hides the transfer accounts, the accounting books show
    # them as one operation: the two reconciled items on 113 disappear and both
    # entries are numbered "BANK/001 (CASH/001)". The rules, one method each:
    #
    # 1. hidden item: on a hidden transfer account and fully reconciled
    #    -> _fg_transfer_pairs()
    # 2. two entries are linked when each has a hidden item on the same
    #    account, in the same full reconciliation, on opposite sides
    #    -> _fg_transfer_pairs()
    # 3. cluster: entries linked directly or through other entries
    #    -> _fg_transfer_clusters()
    # 4. sort key -> _fg_transfer_sort_key()
    # 5. the main entry of a cluster has the smallest sort key; the cluster is
    #    numbered "main (others, sorted by name)" -> _fg_transfer_cluster_name()

    def _fg_get_transfer_links(self):
        """ Tell how the accounting books must present the entries, given the
        hidden transfer accounts of their company.

        :return: {move id: link} for every entry of `self`, where link is a
            dict:

            - `display_name`: number to print for the entry: its name, or
              "main (others)" when it is linked to other entries
            - `sort_key`: tuple ordering the entries in a book; linked entries
              of the same day are adjacent, bank first
            - `linked_move_ids`: ids of the other entries of its cluster,
              including entries that are not in `self`; empty when not linked
            - `hidden_line_ids`: ids of its items the books must not show

            An entry that is not concerned gets its own name, no hidden item
            and the default sort key, so that callers need no special case.
        """
        result = {}
        for company, moves in self.grouped('company_id').items():
            result.update(moves._fg_get_company_transfer_links(company))
        return result

    def _fg_get_company_transfer_links(self, company):
        numbers = self._fg_transfer_document_numbers(self.ids)
        result = {
            move.id: {
                'display_name': numbers[move.id],
                'sort_key': self._fg_transfer_default_sort_key(move.date, numbers[move.id]),
                'linked_move_ids': [],
                'hidden_line_ids': [],
            }
            for move in self
        }
        hidden_account_ids = company._fg_get_hidden_transfer_accounts().ids
        if not hidden_account_ids:
            return result

        # Follow the links until the clusters are complete: an entry outside
        # of `self` can link to yet another entry.
        hidden_line_ids = {}
        links = {}
        frontier = set(self.ids)
        seen = set()
        while frontier:
            seen |= frontier
            lines, pairs = self._fg_transfer_pairs(frontier, hidden_account_ids)
            hidden_line_ids.update(lines)
            frontier = set()
            for move_id, linked_ids in pairs.items():
                links.setdefault(move_id, set()).update(linked_ids)
                for linked_id in linked_ids:
                    links.setdefault(linked_id, set()).add(move_id)
                frontier |= linked_ids - seen

        for move_id, line_ids in hidden_line_ids.items():
            if move_id in result:
                result[move_id]['hidden_line_ids'] = line_ids

        clusters = self._fg_transfer_clusters(links)
        if not clusters:
            return result

        data = self._fg_transfer_move_data(set().union(*clusters), hidden_account_ids, company)
        for cluster in clusters:
            sort_keys = {
                move_id: self._fg_transfer_sort_key(move_id, cluster, data)
                for move_id in cluster
            }
            display_name = self._fg_transfer_cluster_name(cluster, sort_keys, data)
            for move_id in cluster:
                if move_id in result:
                    result[move_id].update({
                        'display_name': display_name,
                        'sort_key': sort_keys[move_id],
                        'linked_move_ids': sorted(cluster - {move_id}),
                    })
        return result

    @api.model
    def _fg_transfer_pairs(self, move_ids, hidden_account_ids):
        """ Rules 1 and 2.

        :return: (hidden_line_ids, pairs) with `hidden_line_ids`
            {move id: [ids of its hidden items]} and `pairs`
            {move id: {ids of the entries it is linked to}}
        """
        self.env['account.move.line'].flush_model(
            ['move_id', 'account_id', 'full_reconcile_id', 'debit', 'credit'])
        rows = self.env.execute_query(SQL(
            """
            SELECT line.move_id, line.id, other.move_id
              FROM account_move_line line
         LEFT JOIN account_move_line other
                ON other.full_reconcile_id = line.full_reconcile_id
               AND other.account_id = line.account_id
               AND other.move_id != line.move_id
               AND (
                    (line.debit > 0 AND other.credit > 0)
                    OR (line.credit > 0 AND other.debit > 0)
               )
             WHERE line.move_id = ANY(%(move_ids)s)
               AND line.account_id = ANY(%(account_ids)s)
               AND line.full_reconcile_id IS NOT NULL
          ORDER BY line.id
            """,
            move_ids=list(move_ids),
            account_ids=list(hidden_account_ids),
        ))
        hidden_line_ids = {}
        pairs = {}
        for move_id, line_id, linked_move_id in rows:
            line_ids = hidden_line_ids.setdefault(move_id, [])
            if line_id not in line_ids:
                line_ids.append(line_id)
            if linked_move_id:
                pairs.setdefault(move_id, set()).add(linked_move_id)
        return hidden_line_ids, pairs

    @api.model
    def _fg_transfer_clusters(self, links):
        """ Rule 3: the connected components of the links.

        :param dict links: {move id: {linked move ids}}, symmetric
        :return: list of sets of move ids, each of two entries or more
        """
        clusters = []
        visited = set()
        for start in links:
            if start in visited:
                continue
            cluster = set()
            queue = [start]
            while queue:
                move_id = queue.pop()
                if move_id in visited:
                    continue
                visited.add(move_id)
                cluster.add(move_id)
                queue.extend(links.get(move_id, ()))
            if len(cluster) > 1:
                clusters.append(cluster)
        return clusters

    @api.model
    def _fg_transfer_move_data(self, move_ids, hidden_account_ids, company):
        """ Read what naming and sorting the linked entries need.

        :return: {move id: {name, date, journal_type, min_account_code}} with
            `name` the number printed on the books and `min_account_code` the
            smallest account code of the items that are not on a hidden
            account
        """
        self.flush_model(['name', 'date', 'journal_id'])
        self.env['account.move.line'].flush_model(['move_id', 'account_id'])
        rows = self.env.execute_query_dict(SQL(
            """
            SELECT move.id,
                   move.name,
                   move.date,
                   journal.type AS journal_type,
                   MIN(account.code_store->>%(root_id)s)
                       FILTER (WHERE NOT line.account_id = ANY(%(account_ids)s)) AS min_account_code
              FROM account_move move
              JOIN account_journal journal ON journal.id = move.journal_id
         LEFT JOIN account_move_line line ON line.move_id = move.id
         LEFT JOIN account_account account ON account.id = line.account_id
             WHERE move.id = ANY(%(move_ids)s)
          GROUP BY move.id, journal.type
            """,
            root_id=str(company.root_id.id),
            move_ids=list(move_ids),
            account_ids=list(hidden_account_ids),
        ))
        # entries are named and ordered by the number printed on the books
        numbers = self._fg_transfer_document_numbers([row['id'] for row in rows])
        for row in rows:
            row['name'] = numbers.get(row['id'], row['name'])
        return {row['id']: row for row in rows}

    @api.model
    def _fg_transfer_document_numbers(self, move_ids):
        """ The numbers printed on the accounting books for the entries.

        This is the name of the entry, unless `fg_vn_accounting_reports` is
        installed: journals can then print the reference instead of the name,
        or drop the trailing sequence number. That module is not a
        dependency: its hook is used when present.

        :return: {move id: number}
        """
        moves = self.browse(move_ids)
        if hasattr(moves, '_fg_get_document_numbers'):
            return moves._fg_get_document_numbers()
        return {move.id: move.name for move in moves}

    @api.model
    def _fg_transfer_default_sort_key(self, date, name):
        """ Sort key of an entry that is not linked: by date, then by name.
        It has the shape of the keys of `_fg_transfer_sort_key`, so that both
        can be compared. """
        name = name or ''
        return (date, name, OTHER_JOURNAL_PRIORITY, '', name)

    @api.model
    def _fg_transfer_sort_key(self, move_id, cluster, data):
        """ Rule 4: (date, smallest name among the entries of the cluster on
        that date, bank / cash / other journal, smallest account code out of
        the hidden accounts, name).

        The second element keeps the linked entries of a same day together, at
        the place of the first of them; entries of other days stay on their
        own day.
        """
        move = data[move_id]
        pair_key = min(
            data[other_id]['name'] or ''
            for other_id in cluster
            if data[other_id]['date'] == move['date']
        )
        return (
            move['date'],
            pair_key,
            JOURNAL_PRIORITY.get(move['journal_type'], OTHER_JOURNAL_PRIORITY),
            move['min_account_code'] or '',
            move['name'] or '',
        )

    @api.model
    def _fg_transfer_cluster_name(self, cluster, sort_keys, data):
        """ Rule 5: "main (others)", the main entry being the first one of the
        cluster in book order and the others being sorted by name. """
        main_id = min(cluster, key=sort_keys.get)
        others = sorted(data[move_id]['name'] or '' for move_id in cluster if move_id != main_id)
        return "%s (%s)" % (data[main_id]['name'] or '', ', '.join(others))
