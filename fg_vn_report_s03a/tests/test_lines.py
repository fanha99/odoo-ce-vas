from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .common import JANUARY, S03aCommon


@tagged('post_install', '-at_install')
class TestS03aLines(S03aCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # an invoice-like entry, a payment and an expense, entered out of date order
        cls.expense = cls._post('2026-01-20', [
            ('642', 300, 0, {'name': "Office supplies"}),
            (cls.cash, 0, 300),
        ], ref="Receipt 77")
        cls.sale = cls._post('2026-01-05', [
            ('131', 110, 0, {'name': "Sale", 'partner_id': cls.partner_a.id}),
            ('511', 0, 100, {'name': "Sale"}),
            ('33311', 0, 10, {'name': "VAT"}),
        ])
        cls.payment = cls._post('2026-01-12', [
            (cls.bank, 110, 0, {'name': "Payment", 'partner_id': cls.partner_a.id}),
            ('131', 0, 110, {'name': "Payment", 'partner_id': cls.partner_a.id}),
        ], journal=cls.bank_journal)
        cls._post('2025-12-31', [('642', 50, 0), (cls.cash, 0, 50)])   # before the period
        cls._post('2026-01-25', [('642', 999, 0), (cls.cash, 0, 999)], post=False)   # draft

    def test_entries_are_in_date_order(self):
        self.assertEqual(
            [line['move_name'] for line in self._lines()],
            [self.sale.name] * 3 + [self.payment.name] * 2 + [self.expense.name] * 2,
        )

    def test_same_day_entries_are_in_number_order(self):
        first = self._post('2026-01-28', [('642', 1, 0), (self.cash, 0, 1)])
        second = self._post('2026-01-28', [('642', 2, 0), (self.cash, 0, 2)])
        names = [line['move_name'] for line in self._lines()][-4:]
        self.assertEqual(names, sorted([first.name, second.name] * 2))

    def test_line_content(self):
        receivable, income, vat = self._lines()[:3]
        self.assertEqual(receivable['id'], 'line_%s' % self.sale.line_ids[0].id)
        self.assertEqual(receivable['move_id'], self.sale.id)
        self.assertEqual(receivable['date_display'], '2026/01/05')
        self.assertEqual(
            (receivable['account_code'], receivable['debit'], receivable['credit'], receivable['description']),
            ('131', 110, 0, "Sale"),
        )
        self.assertEqual((income['account_code'], income['debit'], income['credit']), ('511', 0, 100))
        self.assertEqual((vat['account_code'], vat['description']), ('33311', "VAT"))

    def test_description_falls_back_on_the_entry_reference(self):
        cash_line = self._lines()[-1]
        self.assertEqual(cash_line['account_code'], self.cash.code)
        self.assertEqual(cash_line['description'], "Receipt 77")

    def test_invoice_date_is_shown_when_different(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-03',
            'date': '2026-01-08',
            'invoice_line_ids': [Command.create({'name': "Service", 'quantity': 1, 'price_unit': 100, 'tax_ids': []})],
        })
        invoice.action_post()
        lines = [line for line in self._lines() if line['move_id'] == invoice.id]
        self.assertTrue(lines)
        self.assertEqual({line['date_display'] for line in lines}, {'2026/01/08 (2026/01/03)'})

    def test_notes_sections_and_zero_items_are_left_out(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-09',
            'invoice_line_ids': [
                Command.create({'display_type': 'line_section', 'name': "Section"}),
                Command.create({'name': "Service", 'quantity': 1, 'price_unit': 100, 'tax_ids': []}),
                Command.create({'name': "Free gift", 'quantity': 1, 'price_unit': 0, 'tax_ids': []}),
                Command.create({'display_type': 'line_note', 'name': "Note"}),
            ],
        })
        invoice.action_post()
        self.assertEqual(len(invoice.line_ids), 5)
        lines = [line for line in self._lines() if line['move_id'] == invoice.id]
        self.assertEqual(sorted(line['description'] for line in lines if line['credit']), ["Service"])
        self.assertEqual(len(lines), 2)

    def test_total(self):
        group = self._group()
        self.assertEqual(group['total'], {'debit': 520, 'credit': 520})
        self.assertEqual(group['total_label'], "Total")
        self.assertEqual(group['line_count'], 7)

    def test_empty_period(self):
        group = self._group(date={'date_from': '2024-01-01', 'date_to': '2024-01-31'})
        self.assertEqual(group['lines'], [])
        self.assertEqual(group['total'], {'debit': 0, 'credit': 0})

    def test_other_company_is_not_mixed_in(self):
        other = self.setup_other_company()
        self.env['account.move'].create({
            'move_type': 'entry', 'date': '2026-01-15',
            'journal_id': other['default_journal_misc'].id,
            'line_ids': [
                Command.create({'account_id': other['default_account_expense'].id, 'debit': 7}),
                Command.create({'account_id': other['default_account_revenue'].id, 'credit': 7}),
            ],
        }).action_post()
        self.assertEqual(self._group()['total']['debit'], 520)

    # ---------------------------------------------------------------- filters

    def test_filter_by_journal(self):
        summary = self._summary(journal_ids=self.bank_journal.ids)
        self.assertEqual(summary, [
            (self.payment.name, self.bank.code, 110, 0),
            (self.payment.name, '131', 0, 110),
        ])

    def test_filter_by_entry_type(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2026-01-09',
            'invoice_line_ids': [Command.create({'name': "Service", 'quantity': 1, 'price_unit': 100, 'tax_ids': []})],
        })
        invoice.action_post()
        self.assertEqual({line['move_id'] for line in self._lines(move_type='out_invoice')}, {invoice.id})
        self.assertNotIn(invoice.id, {line['move_id'] for line in self._lines(move_type='entry')})
        self.assertEqual(len(self._lines(move_type='all')), 9)
        self.assertEqual(len(self._lines(move_type='not a type')), 9)

    def test_filter_by_account_keeps_the_matching_items_only(self):
        summary = self._summary(account_ids=self.accounts['131'].ids)
        self.assertEqual(summary, [
            (self.sale.name, '131', 110, 0),
            (self.payment.name, '131', 0, 110),
        ])
        # debit and credit of the journal may differ under this filter
        group = self._group(account_ids=self.accounts['642'].ids)
        self.assertEqual(group['total'], {'debit': 300, 'credit': 0})

    def test_filter_by_partner_keeps_the_matching_items_only(self):
        summary = self._summary(partner_ids=self.partner_a.ids)
        self.assertEqual([(code, debit, credit) for _name, code, debit, credit in summary], [
            ('131', 110, 0), (self.bank.code, 110, 0), ('131', 0, 110),
        ])
        self.assertEqual(self._lines(partner_ids=self.partner_b.ids), [])

    def test_filters_combine(self):
        summary = self._summary(
            journal_ids=self.bank_journal.ids, account_ids=self.accounts['131'].ids,
        )
        self.assertEqual(summary, [(self.payment.name, '131', 0, 110)])

    def test_search_on_the_server(self):
        self.assertEqual(len(self._lines(search='office')), 1)
        self.assertEqual(len(self._lines(search=self.sale.name)), 3)
        self.assertEqual({line['account_code'] for line in self._lines(search='3331')}, {'33311'})
        self.assertEqual(self._lines(search='100%'), [])
        self.assertEqual(self._group(search='office')['total'], {'debit': 300, 'credit': 0})

    # ------------------------------------------------------------------ other

    def test_report_data(self):
        data = self.Report.get_report_data(dict(JANUARY))
        self.assertEqual(data['header']['title'], "GENERAL JOURNAL")
        self.assertEqual(data['header']['template_code'], "Form No. S03a-DNN")
        self.assertEqual(len(data['columns']), 7)
        self.assertFalse(data['lazy'])

    def test_drill_down(self):
        action = self.Report.action_drill_down(dict(JANUARY), {'move_id': self.sale.id})
        self.assertEqual((action['res_model'], action['res_id']), ('account.move', self.sale.id))
        self.assertEqual(action['views'], [(False, 'form')])
        self.assertFalse(self.Report.action_drill_down(dict(JANUARY), {}))

    def test_access(self):
        employee = new_test_user(self.env, login='fg_s03a_employee', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.Report.with_user(employee).get_report_data(dict(JANUARY))
        with self.assertRaises(AccessError):
            self.Report.with_user(employee).get_group_lines(dict(JANUARY), 'journal', 0)
