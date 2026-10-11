from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

JANUARY = {'date': {'date_from': '2026-01-01', 'date_to': '2026-01-31'}, 'lang': 'en_US'}

# code: (account type, code of the parent account)
ACCOUNTS = {
    '111': ('asset_cash', None),
    '1111': ('asset_cash', '111'),
    '1112': ('asset_cash', '111'),
    '113': ('asset_current', None),
    '131': ('asset_receivable', None),
    '1311': ('asset_receivable', '131'),
    '411': ('equity', None),
    '511': ('income', None),
    '642': ('expense', None),
    # off-balance by account type
    'N01': ('off_balance', None),
    'N02': ('off_balance', None),
    # off-balance by code
    '0091': ('asset_current', None),
    '0092': ('asset_current', None),
}


class CDPSCommon(AccountTestInvoicingCommon):
    """ A small set of accounts with a hierarchy, and these posted entries:

        2025-12-15  Dr 1111 1000            / Cr 411 1000
        2026-01-05  Dr 111    50            / Cr 411   50   (posted on a parent account)
        2026-01-08  Dr N01    70            / Cr N02   70   (off-balance, still open)
        2026-01-09  Dr 0091   40            / Cr 0092  40   (off-balance by code...)
        2026-01-19  Dr 0092   40            / Cr 0091  40   (...back to zero)
        2026-01-10  Dr 1311  500 partner A  / Cr 511  500
        2026-01-12  Dr 1112  200            / Cr 1311 200 partner B
        2026-01-20  Dr 642   300            / Cr 1111 300
        2026-01-25  Dr 642   999            / Cr 1111 999   (draft: ignored)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.journal = cls.company_data['default_journal_misc']
        cls.Report = cls.env['vn.report.cdps']

        cls.accounts = {}
        for code, (account_type, parent_code) in ACCOUNTS.items():
            cls.accounts[code] = cls.env['account.account'].create({
                'code': code,
                'name': f"Test {code}",
                'account_type': account_type,
                'reconcile': account_type in ('asset_receivable', 'asset_current'),
                'parent_id': cls.accounts[parent_code].id if parent_code else False,
            })

        cls.partner_debit = cls.env['res.partner'].create({'name': "Partner A"})
        cls.partner_credit = cls.env['res.partner'].create({'name': "Partner B"})

        cls._post('2025-12-15', '1111', '411', 1000)
        cls._post('2026-01-05', '111', '411', 50)
        cls._post('2026-01-08', 'N01', 'N02', 70)
        cls._post('2026-01-09', '0091', '0092', 40)
        cls._post('2026-01-19', '0092', '0091', 40)
        cls._post('2026-01-10', '1311', '511', 500, debit_partner=cls.partner_debit)
        cls._post('2026-01-12', '1112', '1311', 200, credit_partner=cls.partner_credit)
        cls._post('2026-01-20', '642', '1111', 300)
        cls._post('2026-01-25', '642', '1111', 999, post=False)

    @classmethod
    def _post(cls, date, debit_code, credit_code, amount, debit_partner=None, credit_partner=None, post=True):
        move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': date,
            'journal_id': cls.journal.id,
            'line_ids': [
                Command.create({
                    'account_id': cls.accounts[debit_code].id,
                    'partner_id': debit_partner and debit_partner.id,
                    'debit': amount,
                }),
                Command.create({
                    'account_id': cls.accounts[credit_code].id,
                    'partner_id': credit_partner and credit_partner.id,
                    'credit': amount,
                }),
            ],
        })
        if post:
            move.action_post()
        return move

    def _report(self, **options):
        """ Return the single group of the report. """
        return self.Report.get_report_data({**JANUARY, **options})['lines'][0]

    def _lines(self, **options):
        """ Return the lines of the report by account code. """
        return {line['code']: line for line in self._report(**options)['lines']}

    def assertFigures(self, line, opening_debit=0, opening_credit=0, debit=0, credit=0, closing_debit=0, closing_credit=0):
        self.assertEqual(
            [line[fname] for fname in (
                'opening_debit', 'opening_credit', 'debit', 'credit', 'closing_debit', 'closing_credit',
            )],
            [opening_debit, opening_credit, debit, credit, closing_debit, closing_credit],
            f"Figures of {line.get('code', 'the total')}",
        )
