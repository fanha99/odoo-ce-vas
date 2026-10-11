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


class S03aCommon(AccountTestInvoicingCommon):
    """ Accounts with Vietnamese codes, and helpers to post entries.

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
        cls.Report = cls.env['vn.report.s03a']

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

    def _group(self, **options):
        """ Return the single group of the journal. """
        groups = self.Report.get_report_data({**JANUARY, **options})['lines']
        self.assertEqual(len(groups), 1)
        return groups[0]

    def _lines(self, **options):
        return self._group(**options)['lines']

    def _summary(self, **options):
        """ The lines as (number, account code, debit, credit). """
        return [
            (line['move_name'], line['account_code'], line['debit'], line['credit'])
            for line in self._lines(**options)
        ]
