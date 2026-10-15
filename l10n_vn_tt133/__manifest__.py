{
    'name': 'Vietnam - SME Chart of Accounts (Circular 133/2016)',
    'version': '20.0.1.0.0',
    'countries': ['vn'],
    'category': 'Accounting/Localizations/Account Charts',
    'summary': 'Chart of accounts for small and medium enterprises, Circular 133/2016/TT-BTC',
    # Without a description, Odoo renders readme.md as reStructuredText and
    # chokes on its Markdown tables.
    'description': """
Vietnam - SME Chart of Accounts (Circular 133/2016/TT-BTC)
===========================================================

Chart of accounts template for small, medium and micro enterprises applying
Circular 133/2016/TT-BTC (replacing Decision 48/2006/QD-BTC since 2017-01-01).
Not for companies with more than 50% state capital, nor for cooperatives.

* summary accounts (111, 112, 333, 642...) as parents of the detail accounts
* technical accounts for bank operations outside the chart: 03, 031, 032, 021
* the VAT taxes of l10n_vn, booked on the accounts of the Circular
* continental accounting: cost of goods sold booked on delivery

See readme.md in the module directory.
""",
    'author': 'Fanha Giang',
    'website': 'https://github.com/fanha99',
    'license': 'AGPL-3',
    'depends': ['l10n_vn'],
    'installable': True,
}
