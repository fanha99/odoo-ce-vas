from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

JANUARY = {'date': {'date_from': '2026-01-01', 'date_to': '2026-01-31'}, 'lang': 'en_US'}

# code: account type
ACCOUNTS = {
    '131': 'asset_receivable',
    '331': 'liability_payable',
    '411': 'equity',
    '511': 'income',
    '642': 'expense',
    '33311': 'liability_current',
}


class S03bCommon(AccountTestInvoicingCommon):
    """ Accounts with Vietnamese codes and these posted entries:

        2025-12-10  Dr cash 1000            / Cr 411  1000
        2025-12-10  Dr 131   200 partner A  / Cr 511   200
        2026-01-05  Dr 131   110 partner A  / Cr 511   100, Cr 33311 10   (the sale)
        2026-01-12  Dr bank  110 partner A  / Cr 131   110 partner A      (the payment)
        2026-01-20  Dr 642   300            / Cr cash  300                (the expense)
        2026-01-25  Dr 642   999            / Cr cash  999                (draft: ignored)

    The cash, bank and transfer accounts are the ones of the test company:
    `cls.cash`, `cls.bank`, `cls.transfer`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.misc_journal = cls.company_data['default_journal_misc']
        cls.cash_journal = cls.company_data['default_journal_cash']
        cls.bank_journal = cls.company_data['default_journal_bank']
        cls.cash = cls.cash_journal.default_account_id
        cls.bank = cls.bank_journal.default_account_id
        cls.transfer = cls.company.transfer_account_id
        cls.Report = cls.env['vn.report.s03b']

        cls.accounts = {
            code: cls.env['account.account'].create({
                'code': code,
                'name': f"Test {code}",
                'account_type': account_type,
                'reconcile': account_type in ('asset_receivable', 'liability_payable'),
            })
            for code, account_type in ACCOUNTS.items()
        }
        cls.partner_a = cls.env['res.partner'].create({'name': "Partner A"})
        cls.partner_b = cls.env['res.partner'].create({'name': "Partner B"})
        partner_a = {'partner_id': cls.partner_a.id}

        cls._post('2025-12-10', [(cls.cash, 1000, 0), ('411', 0, 1000)])
        cls._post('2025-12-10', [('131', 200, 0, partner_a), ('511', 0, 200)])
        cls.sale = cls._post('2026-01-05', [
            ('131', 110, 0, {'name': "Sale", **partner_a}),
            ('511', 0, 100, {'name': "Sale"}),
            ('33311', 0, 10, {'name': "VAT"}),
        ])
        cls.payment = cls._post('2026-01-12', [
            (cls.bank, 110, 0, {'name': "Payment", **partner_a}),
            ('131', 0, 110, {'name': "Payment", **partner_a}),
        ], journal=cls.bank_journal)
        cls.expense = cls._post('2026-01-20', [
            ('642', 300, 0, {'name': "Office supplies"}),
            (cls.cash, 0, 300),
        ], ref="Receipt 77")
        cls._post('2026-01-25', [('642', 999, 0), (cls.cash, 0, 999)], post=False)

    @classmethod
    def _account(cls, account):
        return cls.accounts[account] if isinstance(account, str) else account

    @classmethod
    def _post(cls, date, lines, journal=None, ref=None, post=True):
        """ Create an entry. `lines` is a list of (account, debit, credit) or
        (account, debit, credit, {extra values}). """
        line_ids = []
        for account, debit, credit, *extra in lines:
            line_ids.append(Command.create({
                'account_id': cls._account(account).id,
                'debit': debit,
                'credit': credit,
                **(extra[0] if extra else {}),
            }))
        move = cls.env['account.move'].create({
            'move_type': 'entry',
            'date': date,
            'journal_id': (journal or cls.misc_journal).id,
            'ref': ref,
            'line_ids': line_ids,
        })
        if post:
            move.action_post()
        return move

    @classmethod
    def _deposit(cls, date, amount, bank_date=None, reconcile=True):
        """ Cash deposited at the bank: the cash entry and the bank entry,
        meeting on the transfer account. """
        cash_move = cls._post(date, [
            (cls.transfer, amount, 0, {'name': "Deposit"}),
            (cls.cash, 0, amount, {'name': "Deposit"}),
        ], journal=cls.cash_journal)
        bank_move = cls._post(bank_date or date, [
            (cls.bank, amount, 0, {'name': "Received"}),
            (cls.transfer, 0, amount, {'name': "Received"}),
        ], journal=cls.bank_journal)
        if reconcile:
            (cash_move + bank_move).line_ids.filtered(
                lambda line: line.account_id == cls.transfer).reconcile()
        return cash_move, bank_move

    @classmethod
    def _hide_transfer_account(cls, accounts=None):
        cls.company.write({
            'fg_hide_transfer_account': True,
            'fg_hidden_transfer_account_ids': (accounts or cls.transfer).ids,
        })

    def _code(self, account):
        return self._account(account).code

    def _groups(self, **options):
        """ The accounts of the ledger by account code. """
        groups = self.Report.get_report_data({**JANUARY, **options})['lines']
        return {group['code']: group for group in groups}

    def _ledger(self, account, **options):
        return self._groups(**options)[self._code(account)]

    def _summary(self, account, **options):
        """ The lines of an account as (number, counterpart, debit, credit). """
        return [
            (line['move_name'], line['counterpart_account'], line['debit'], line['credit'])
            for line in self._ledger(account, **options)['lines']
        ]
