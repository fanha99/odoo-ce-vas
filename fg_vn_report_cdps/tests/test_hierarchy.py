from odoo.tests import tagged

from .common import CDPSCommon


@tagged('post_install', '-at_install')
class TestCDPSHierarchy(CDPSCommon):

    def test_parent_sums_itself_and_its_children(self):
        lines = self._lines(hierarchy=True)
        # 111 has an entry of its own (50) besides its children
        self.assertFigures(
            lines['111'], opening_debit=1000, debit=250, credit=300, closing_debit=950,
        )
        self.assertFigures(lines['1111'], opening_debit=1000, credit=300, closing_debit=700)
        self.assertFigures(
            lines['131'], debit=500, credit=200, closing_debit=500, closing_credit=200,
        )

    def test_tree_structure(self):
        lines = self._lines(hierarchy=True)
        parent = lines['111']
        self.assertEqual((parent['level'], parent['parent_id']), (0, None))
        self.assertTrue(parent['is_parent'])
        self.assertTrue(parent['has_children'])
        for code in ('1111', '1112'):
            self.assertEqual(lines[code]['level'], 1)
            self.assertEqual(lines[code]['parent_id'], parent['id'])
            self.assertFalse(lines[code]['has_children'])
        self.assertFalse(lines['411']['is_parent'])

    def test_children_follow_their_parent(self):
        codes = [line['code'] for line in self._report(hierarchy=True)['lines']]
        start = codes.index('111')
        self.assertEqual(codes[start:start + 3], ['111', '1111', '1112'])
        start = codes.index('131')
        self.assertEqual(codes[start:start + 2], ['131', '1311'])

    def test_grand_total_does_not_count_twice(self):
        flat = self._report()['totals']
        tree = self._report(hierarchy=True)['totals']
        self.assertEqual(flat, tree)
        self.assertEqual(tree['closing_debit'], 1820)

    def test_root_lines_add_up_to_the_grand_total(self):
        report = self._report(hierarchy=True)
        for fname in ('opening_debit', 'debit', 'credit', 'closing_debit', 'closing_credit'):
            self.assertEqual(
                sum(line[fname] for line in report['lines'] if line['level'] == 0),
                report['totals'][fname],
                fname,
            )

    def test_parent_without_own_figures_is_shown(self):
        """ 131 has no entry of its own, but its child has. """
        self.assertNotIn('131', self._lines())
        self.assertIn('131', self._lines(hierarchy=True))

    def test_empty_branch_is_hidden(self):
        child = self.env['account.account'].create({
            'code': '1132', 'name': "Test 1132", 'account_type': 'asset_current',
            'parent_id': self.accounts['113'].id,
        })
        self.assertNotIn('113', self._lines(hierarchy=True))
        lines = self._lines(hierarchy=True, show_zero_balance=True)
        self.assertTrue(lines['113']['has_children'])
        self.assertEqual(lines['1132']['parent_id'], lines['113']['id'])
        self.assertEqual(lines['1132']['account_id'], child.id)

    def test_filtered_out_parent_is_skipped(self):
        """ Only 1111 is selected: its parent is not in the report, so it
        becomes a root line. """
        report = self._report(hierarchy=True, account_ids=self.accounts['1111'].ids)
        self.assertEqual(len(report['lines']), 1)
        line = report['lines'][0]
        self.assertEqual((line['code'], line['level'], line['parent_id']), ('1111', 0, None))

    def test_hidden_transfer_parent_does_not_hide_its_children(self):
        child = self.env['account.account'].create({
            'code': '1131', 'name': "Test 1131", 'account_type': 'asset_current',
            'reconcile': True, 'parent_id': self.accounts['113'].id,
        })
        self.accounts['1131'] = child
        self._post('2026-01-15', '1131', '1111', 100)
        self.company.write({
            'fg_hide_transfer_account': True,
            'fg_hidden_transfer_account_ids': self.accounts['113'].ids,
        })
        lines = self._lines(hierarchy=True)
        self.assertNotIn('113', lines)
        self.assertEqual((lines['1131']['level'], lines['1131']['parent_id']), (0, None))
        totals = self._report(hierarchy=True)['totals']
        self.assertEqual(totals['closing_debit'], totals['closing_credit'])

    def test_three_levels(self):
        grandchild = self.env['account.account'].create({
            'code': '11111', 'name': "Test 11111", 'account_type': 'asset_cash',
            'parent_id': self.accounts['1111'].id,
        })
        self.accounts['11111'] = grandchild
        self._post('2026-01-22', '11111', '411', 25)
        lines = self._lines(hierarchy=True)
        self.assertEqual(lines['11111']['level'], 2)
        self.assertEqual(lines['11111']['parent_id'], lines['1111']['id'])
        self.assertTrue(lines['1111']['is_parent'])
        self.assertFigures(
            lines['1111'], opening_debit=1000, debit=25, credit=300, closing_debit=725,
        )
        self.assertFigures(
            lines['111'], opening_debit=1000, debit=275, credit=300, closing_debit=975,
        )
