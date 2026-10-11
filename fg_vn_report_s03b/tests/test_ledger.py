from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .common import JANUARY, S03bCommon


@tagged('post_install', '-at_install')
class TestS03bLedger(S03bCommon):

    def test_receivable_ledger(self):
        ledger = self._ledger('131')
        self.assertEqual(ledger['id'], 'account_%s' % self.accounts['131'].id)
        self.assertEqual(ledger['name'], "131 - Test 131")
        self.assertEqual(ledger['label'], "Account: 131 - Test 131")
        self.assertEqual(ledger['opening'], {'debit': 200, 'credit': 0})
        self.assertEqual(ledger['total'], {'debit': 110, 'credit': 110})
        self.assertEqual(ledger['closing'], {'debit': 200, 'credit': 0})
        self.assertEqual(ledger['line_count'], 2)
        self.assertEqual(
            (ledger['opening_label'], ledger['total_label'], ledger['closing_label']),
            ("Opening balance", "Total of the period", "Closing balance"),
        )

    def test_balance_side(self):
        income = self._ledger('511')
        self.assertEqual(income['opening'], {'debit': 0, 'credit': 200})
        self.assertEqual(income['closing'], {'debit': 0, 'credit': 300})
        cash = self._ledger(self.cash)
        self.assertEqual(cash['opening'], {'debit': 1000, 'credit': 0})
        self.assertEqual(cash['closing'], {'debit': 700, 'credit': 0})
        # an account ending at zero has an empty closing balance
        self._post('2026-01-30', [('511', 300, 0), ('411', 0, 300)])
        self.assertEqual(self._ledger('511')['closing'], {'debit': 0, 'credit': 0})

    def test_line_content(self):
        sale_line, payment_line = self._ledger('131')['lines']
        self.assertEqual(sale_line['id'], 'line_%s' % self.sale.line_ids[0].id)
        self.assertEqual(sale_line['move_id'], self.sale.id)
        self.assertEqual(sale_line['date_display'], '2026/01/05')
        self.assertEqual(sale_line['move_name'], self.sale.name)
        self.assertEqual(sale_line['description'], "Sale")
        self.assertEqual((sale_line['debit'], sale_line['credit']), (110, 0))
        self.assertEqual((payment_line['debit'], payment_line['credit']), (0, 110))
        # running balance, kept in the data though no column prints it
        self.assertEqual([sale_line['balance'], payment_line['balance']], [310, 200])

    def test_description_falls_back_on_the_entry_reference(self):
        cash_line = self._ledger(self.cash)['lines'][0]
        self.assertEqual(cash_line['description'], "Receipt 77")

    def test_lines_are_in_date_then_number_order(self):
        late = self._post('2026-01-28', [('131', 5, 0), ('511', 0, 5)])
        early = self._post('2026-01-02', [('131', 7, 0), ('511', 0, 7)])
        names = [line['move_name'] for line in self._ledger('131')['lines']]
        self.assertEqual(names, [early.name, self.sale.name, self.payment.name, late.name])

    def test_draft_entries_are_ignored(self):
        expense = self._ledger('642')
        self.assertEqual(expense['total'], {'debit': 300, 'credit': 0})
        self.assertEqual(len(expense['lines']), 1)

    def test_accounts_are_ordered_by_code(self):
        codes = list(self._groups())
        self.assertEqual(codes, sorted(codes))

    # -------------------------------------------- accounts without journal items

    def test_accounts_without_items_are_left_out_by_default(self):
        groups = self._groups()
        self.assertNotIn('411', groups, "an opening balance but no item in the period")
        self.assertNotIn('331', groups, "nothing at all")
        self.assertIn('131', groups)

    def test_accounts_with_an_opening_balance(self):
        groups = self._groups(empty_accounts='with_balance')
        self.assertEqual(groups['411']['opening'], {'debit': 0, 'credit': 1000})
        self.assertEqual(groups['411']['closing'], {'debit': 0, 'credit': 1000})
        self.assertEqual(groups['411']['lines'], [])
        self.assertNotIn('331', groups)

    def test_all_accounts(self):
        groups = self._groups(empty_accounts='all')
        self.assertIn('411', groups)
        self.assertEqual(groups['331']['closing'], {'debit': 0, 'credit': 0})

    def test_option_of_the_previous_versions(self):
        self.assertIn('331', self._groups(show_zero_balance=True))
        self.assertNotIn('331', self._groups(show_zero_balance=False))
        self.assertNotIn('331', self._groups(show_zero_balance=True, empty_accounts='hide'))

    # ---------------------------------------------------------------- filters

    def test_filter_by_account(self):
        groups = self._groups(account_ids=(self.accounts['131'] + self.accounts['642']).ids)
        self.assertEqual(list(groups), ['131', '642'])

    def test_filter_by_account_type(self):
        groups = self._groups(account_type='income')
        self.assertEqual(list(groups), ['511'])
        self.assertEqual(list(self._groups(account_type='expense')), ['642'])
        liabilities = self._groups(account_type='liability', empty_accounts='all')
        self.assertIn('33311', liabilities)
        self.assertIn('331', liabilities)
        self.assertNotIn('131', liabilities)
        self.assertIn('131', self._groups(account_type='all'))

    def test_filter_by_partner_applies_to_the_opening_balance(self):
        self._post('2025-12-20', [('131', 40, 0, {'partner_id': self.partner_b.id}), ('511', 0, 40)])
        self._post('2026-01-07', [('131', 15, 0, {'partner_id': self.partner_b.id}), ('511', 0, 15)])
        everyone = self._ledger('131')
        self.assertEqual(everyone['opening'], {'debit': 240, 'credit': 0})
        partner_b = self._ledger('131', partner_ids=self.partner_b.ids)
        self.assertEqual(partner_b['opening'], {'debit': 40, 'credit': 0})
        self.assertEqual(partner_b['total'], {'debit': 15, 'credit': 0})
        self.assertEqual(partner_b['closing'], {'debit': 55, 'credit': 0})
        self.assertEqual(len(partner_b['lines']), 1)

    def test_filter_by_journal(self):
        ledger = self._ledger('131', journal_ids=self.bank_journal.ids)
        self.assertEqual(ledger['opening'], {'debit': 0, 'credit': 0})
        self.assertEqual(ledger['total'], {'debit': 0, 'credit': 110})
        self.assertEqual(ledger['closing'], {'debit': 0, 'credit': 110})

    # ------------------------------------------------------------ off-balance

    def test_off_balance_account_needs_a_balance(self):
        Account = self.env['account.account']
        first = Account.create({'code': 'N01', 'name': "Off 1", 'account_type': 'off_balance'})
        second = Account.create({'code': 'N02', 'name': "Off 2", 'account_type': 'off_balance'})
        by_code = Account.create({'code': '0091', 'name': "Off by code", 'account_type': 'asset_current'})
        self.accounts.update({'N01': first, 'N02': second, '0091': by_code})
        # N01 / N02 keep a balance; 0091 moves and comes back to zero
        self._post('2026-01-08', [('N01', 70, 0), ('N02', 0, 70)])
        self._post('2026-01-09', [('0091', 40, 0), ('411', 0, 40)])
        self._post('2026-01-19', [('411', 40, 0), ('0091', 0, 40)])

        groups = self._groups()
        self.assertEqual(groups['N01']['closing'], {'debit': 70, 'credit': 0})
        self.assertNotIn('0091', groups)
        self.assertNotIn('0091', self._groups(empty_accounts='all'))
        # the rule does not apply to the accounts the user selected
        self.assertEqual(len(self._ledger('0091', account_ids=by_code.ids)['lines']), 2)

    # ------------------------------------------------------------------ other

    def test_other_company_is_not_mixed_in(self):
        other = self.setup_other_company()
        account_ids = [group['account_id'] for group in self._groups(empty_accounts='all').values()]
        self.assertNotIn(other['default_account_revenue'].id, account_ids)
        self.assertEqual(
            self.Report.get_report_data({**JANUARY, 'account_ids': other['default_account_revenue'].ids})['lines'],
            [],
        )

    def test_report_data(self):
        data = self.Report.get_report_data(dict(JANUARY))
        self.assertEqual(data['header']['title'], "GENERAL LEDGER")
        self.assertEqual(data['header']['template_code'], "Form No. S03b-DNN")
        self.assertEqual(len(data['columns']), 6)
        self.assertFalse(data['lazy'])

    def test_drill_down(self):
        action = self.Report.action_drill_down(dict(JANUARY), {'move_id': self.sale.id})
        self.assertEqual((action['res_model'], action['res_id']), ('account.move', self.sale.id))

        account = self.accounts['131']
        action = self.Report.action_drill_down(
            {**JANUARY, 'partner_ids': self.partner_a.ids, 'journal_ids': self.bank_journal.ids},
            {'account_id': account.id},
        )
        items = self.env['account.move.line'].search(action['domain'])
        self.assertEqual(items, self.payment.line_ids.filtered(lambda line: line.account_id == account))
        self.assertFalse(self.Report.action_drill_down(dict(JANUARY), {}))

    def test_access(self):
        employee = new_test_user(self.env, login='fg_s03b_employee', groups='base.group_user')
        Report = self.Report.with_user(employee)
        with self.assertRaises(AccessError):
            Report.get_report_data(dict(JANUARY))
        with self.assertRaises(AccessError):
            Report.get_group_lines(dict(JANUARY), 'account_%s' % self.accounts['131'].id, 0)

    def test_query_count_does_not_depend_on_the_number_of_accounts(self):

        def count_queries():
            self.env.flush_all()
            self.env.invalidate_all()
            start = self.env.cr.sql_log_count
            self.Report._get_lines({**JANUARY, 'company_id': self.company.id})
            return self.env.cr.sql_log_count - start

        count_queries()  # warm up the caches that do not depend on the data
        before = count_queries()
        for index in range(8):
            account = self.env['account.account'].create({
                'code': f'64{index + 3}', 'name': f"Extra {index}", 'account_type': 'expense',
            })
            self._post('2026-01-21', [(account, 10 + index, 0), (self.cash, 0, 10 + index)])
        self.assertEqual(count_queries(), before)
