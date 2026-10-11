from odoo.tests import tagged

from .common import CDPSCommon


@tagged('post_install', '-at_install')
class TestCDPSBalances(CDPSCommon):

    def test_balances_and_movements(self):
        lines = self._lines()
        self.assertFigures(lines['1111'], opening_debit=1000, credit=300, closing_debit=700)
        self.assertFigures(lines['1112'], debit=200, closing_debit=200)
        self.assertFigures(lines['111'], debit=50, closing_debit=50)
        self.assertFigures(lines['411'], opening_credit=1000, credit=50, closing_credit=1050)
        self.assertFigures(lines['511'], credit=500, closing_credit=500)

    def test_draft_entries_are_ignored(self):
        self.assertFigures(self._lines()['642'], debit=300, closing_debit=300)

    def test_receivable_is_split_by_partner(self):
        """ Partner A owes 500 and partner B paid 200 in advance: the two
        balances are not netted. """
        line = self._lines()['1311']
        self.assertFigures(line, debit=500, credit=200, closing_debit=500, closing_credit=200)

    def test_receivable_opening_is_split_by_partner(self):
        line = self._lines(date={'date_from': '2026-02-01', 'date_to': '2026-02-28'})['1311']
        self.assertFigures(
            line, opening_debit=500, opening_credit=200, closing_debit=500, closing_credit=200,
        )

    def test_grand_total(self):
        totals = self._report()['totals']
        self.assertFigures(
            totals,
            opening_debit=1000, opening_credit=1000,
            debit=1120, credit=1120,
            closing_debit=1820, closing_credit=1820,
        )

    def test_accounts_without_figures(self):
        self.assertNotIn('131', self._lines())
        self.assertNotIn('113', self._lines())
        lines = self._lines(show_zero_balance=True)
        self.assertFigures(lines['131'])
        self.assertFigures(lines['113'])
        # the screen filter is the reverse of the wizard option
        self.assertIn('131', self._lines(hide_zero=False))
        self.assertNotIn('131', self._lines(hide_zero=True))

    def test_account_filter(self):
        account_ids = (self.accounts['1111'] + self.accounts['642']).ids
        report = self._report(account_ids=account_ids)
        self.assertEqual([line['code'] for line in report['lines']], ['1111', '642'])
        self.assertFigures(
            report['totals'], opening_debit=1000, debit=300, credit=300, closing_debit=1000,
        )

    def test_lines_are_ordered_by_code(self):
        codes = [line['code'] for line in self._report()['lines']]
        self.assertEqual(codes, sorted(codes))

    def test_account_names_follow_the_report_language(self):
        self.env['res.lang']._activate_lang('vi_VN')
        self.accounts['1111'].with_context(lang='vi_VN').name = "Tiền Việt Nam"
        self.assertEqual(self._lines()['1111']['name'], "Test 1111")
        self.assertEqual(self._lines(lang='vi_VN')['1111']['name'], "Tiền Việt Nam")
        # an account not translated falls back on its source name
        self.assertEqual(self._lines(lang='vi_VN')['1112']['name'], "Test 1112")

    # ------------------------------------------------------------ off-balance

    def test_off_balance_account_with_balance(self):
        lines = self._lines()
        self.assertTrue(lines['N01']['is_off_balance'])
        self.assertFigures(lines['N01'], debit=70, closing_debit=70)
        self.assertFigures(lines['N02'], credit=70, closing_credit=70)
        self.assertFalse(lines['1111']['is_off_balance'])

    def test_off_balance_account_without_balance_is_hidden(self):
        """ 0091 and 0092 moved in the period but are back to zero. """
        for options in ({}, {'show_zero_balance': True}, {'hierarchy': True}):
            lines = self._lines(**options)
            self.assertNotIn('0091', lines)
            self.assertNotIn('0092', lines)

    def test_off_balance_by_code_with_balance(self):
        self._post('2026-01-21', '0091', '0092', 15)
        lines = self._lines()
        self.assertTrue(lines['0091']['is_off_balance'])
        self.assertFigures(lines['0091'], debit=55, credit=40, closing_debit=15)
        totals = self._report()['totals']
        self.assertEqual(totals['closing_debit'], totals['closing_credit'])
        self.assertEqual(totals['closing_debit'], 1835)

    # ------------------------------------------------------ transfer accounts

    def _transfer(self, complete=True):
        self._post('2026-01-15', '113', '1111', 100)
        if complete:
            self._post('2026-01-16', '1112', '113', 100)

    def test_transfer_account_is_shown_by_default(self):
        self._transfer()
        self.assertFigures(self._lines()['113'], debit=100, credit=100)
        self.assertEqual(self._report()['totals']['debit'], 1320)

    def test_hidden_transfer_account_without_balance(self):
        self._transfer()
        self.company.write({
            'fg_hide_transfer_account': True,
            'fg_hidden_transfer_account_ids': self.accounts['113'].ids,
        })
        self.assertNotIn('113', self._lines())
        self.assertNotIn('113', self._lines(show_zero_balance=True))
        totals = self._report()['totals']
        self.assertEqual((totals['debit'], totals['credit']), (1220, 1220))

    def test_hidden_transfer_account_with_balance(self):
        """ Money left one account and has not reached the other yet. """
        self._transfer(complete=False)
        self.company.write({
            'fg_hide_transfer_account': True,
            'fg_hidden_transfer_account_ids': self.accounts['113'].ids,
        })
        self.assertFigures(self._lines()['113'], debit=100, closing_debit=100)
        totals = self._report()['totals']
        self.assertEqual(totals['closing_debit'], totals['closing_credit'])
        self.assertEqual((totals['debit'], totals['credit']), (1220, 1220))

    def test_setting_off_ignores_the_selected_accounts(self):
        self._transfer()
        self.company.fg_hidden_transfer_account_ids = self.accounts['113']
        self.assertIn('113', self._lines())

    # ---------------------------------------------------------------- data

    def test_report_data(self):
        data = self.Report.get_report_data({'date': {'date_from': '2026-01-01', 'date_to': '2026-01-31'}, 'lang': 'en_US'})
        self.assertEqual(data['header']['title'], "TRIAL BALANCE")
        self.assertEqual(len(data['columns']), 8)
        report = data['lines'][0]
        self.assertEqual(report['total_label'], "TOTAL")
        self.assertFalse(report['has_comparison'])
        self.assertFalse(report['show_hierarchy'])
        line = report['lines'][0]
        self.assertEqual(line['id'], f"account_{line['account_id']}")
        self.assertEqual((line['level'], line['parent_id'], line['is_parent']), (0, None, False))

    def test_drill_down(self):
        account = self.accounts['111']
        action = self.Report.action_drill_down(dict(self.env.context, **{
            'date': {'date_from': '2026-01-01', 'date_to': '2026-01-31'},
            'company_id': self.company.id,
        }), {'account_id': account.id})
        self.assertEqual(action['res_model'], 'account.move.line')
        items = self.env['account.move.line'].search(action['domain'])
        # the items of the parent account and of its children, in the period
        self.assertEqual(sorted(items.mapped('account_id.code')), ['111', '1111', '1112'])
        self.assertEqual(sum(items.mapped('debit')), 250)
        self.assertFalse(self.Report.action_drill_down({}, {}))
