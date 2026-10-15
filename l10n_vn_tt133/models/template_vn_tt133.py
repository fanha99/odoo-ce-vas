# Part of odoo-ce-vas. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.addons.account.models.chart_template import template

# Accounts Odoo needs for bank operations: outside the chart of the Circular,
# code starting with 0, no parent account (readme.md section 3.3).
TECHNICAL_ACCOUNT_XMLIDS = (
    'vn133_chart113',
    'account_journal_payment_debit_account_id',
    'account_journal_payment_credit_account_id',
    'vn133_chart021',
)


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('vn_tt133')
    def _get_vn_tt133_template_data(self):
        return {
            'name': _("SME accounting (Circular 133/2016/TT-BTC)"),
            # '2' keeps the codes of the Circular as they are: 131 stays 131
            # and the technical accounts 03, 031... are not padded with 0.
            'code_digits': '2',
        }

    @template('vn_tt133', 'res.company')
    def _get_vn_tt133_res_company(self):
        company_values = {
            'display_invoice_amount_total_words': True,
            'anglo_saxon_accounting': False,
            'account_fiscal_country_id': 'base.vn',
            'bank_account_code_prefix': '112',
            'cash_account_code_prefix': '111',
            'transfer_account_code_prefix': '03',
            'transfer_account_id': 'vn133_chart113',
            'account_default_pos_receivable_account_id': 'vn133_chart131',
            'income_currency_exchange_account_id': 'vn133_chart515',
            'expense_currency_exchange_account_id': 'vn133_chart635',
            'account_journal_early_pay_discount_loss_account_id': 'vn133_chart635',
            'account_journal_early_pay_discount_gain_account_id': 'vn133_chart515',
            'account_sale_tax_id': 'tax_sale_vat10',
            'account_purchase_tax_id': 'tax_purchase_vat10',
            'expense_account_id': 'vn133_chart6421',
            'income_account_id': 'vn133_chart5111',
            'receivable_account_id': 'vn133_chart131',
            'payable_account_id': 'vn133_chart331',
            # the three keys below are fields of Enterprise (deferred) and mrp_account:
            # the loader skips them when the module is not installed
            'deferred_expense_account_id': 'vn133_chart242',
            'deferred_revenue_account_id': 'vn133_chart3387',
            'account_production_wip_account_id': 'vn133_chart154',
            'default_cash_difference_income_account_id': 'vn133_chart711',
            'default_cash_difference_expense_account_id': 'vn133_chart811',
            'tax_calculation_rounding_method': 'round_per_line',
            'account_stock_valuation_id': 'vn133_chart156',
            'account_journal_suspense_account_id': 'vn133_chart021',
        }
        return {self.env.company.id: company_values}

    @template('vn_tt133', 'account.account')
    def _get_vn_tt133_account_account(self):
        return {
            f'vn133_chart{code}': {'account_stock_variation_id': 'vn133_chart632'}
            for code in ('152', '153', '155', '156')
        }

    @template('vn_tt133', 'account.journal')
    def _get_vn_tt133_account_journal(self):
        return {
            'bank': {'default_account_id': 'vn133_chart1121'},
            'cash': {
                'name': self.env._("Cash"),
                'type': 'cash',
                'default_account_id': 'vn133_chart1111',
            },
        }

    # VAT depends on the tax law, not on the accounting regime: the taxes of
    # l10n_vn are loaded as they are, booked on the TT133 accounts of the same code.

    @template('vn_tt133', 'account.tax.group')
    def _get_vn_tt133_account_tax_group(self):
        return self._parse_csv('vn', 'account.tax.group')

    @template('vn_tt133', 'account.tax')
    def _get_vn_tt133_account_tax(self):
        tax_data = self._parse_csv('vn', 'account.tax')
        self._deref_account_tags('vn', tax_data)
        accounts = self._parse_csv('vn_tt133', 'account.account')

        def tt133_account(xmlid):
            tt133_xmlid = f'vn133_{xmlid}'
            if tt133_xmlid not in accounts:
                raise ValueError(f"l10n_vn tax account {xmlid} has no {tt133_xmlid} in the TT133 chart of accounts")
            return tt133_xmlid

        for values in tax_data.values():
            if values.get('cash_basis_transition_account_id'):
                values['cash_basis_transition_account_id'] = tt133_account(values['cash_basis_transition_account_id'])
            for field_name in ('repartition_line_ids', 'invoice_repartition_line_ids', 'refund_repartition_line_ids'):
                for command in values.get(field_name, []):
                    line = command[2] if isinstance(command, (list, tuple)) and len(command) == 3 else None
                    if isinstance(line, dict) and line.get('account_id'):
                        line['account_id'] = tt133_account(line['account_id'])
        return tax_data

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'vn_tt133':
            return {
                '111': 'vn133_chart111',
                '112': 'vn133_chart112',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)

    def _post_load_data(self, template_code, company, template_data):
        res = super()._post_load_data(template_code, company, template_data)
        if template_code == 'vn_tt133' and not (company or self.env.company).parent_id:
            # Odoo has just put the suspense and outstanding accounts under 112
            # (bank prefix, see _get_account_parent_xmlid): take them out.
            for xmlid in TECHNICAL_ACCOUNT_XMLIDS:
                account = self.ref(xmlid, raise_if_not_found=False)
                if account and account.parent_id:
                    account.parent_id = False
        return res
