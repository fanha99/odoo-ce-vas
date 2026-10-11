from odoo import _, models
from odoo.exceptions import AccessError


class VNReportAccessMixin(models.AbstractModel):
    """ Access control shared by the Vietnamese reports.

    A report is an AbstractModel, so no access right protects it, and it reads
    its figures with raw SQL, so no record rule applies either. Every public
    method (reachable through RPC or an export URL) must call
    `_check_report_access()` before returning figures.
    """
    _name = 'vn.report.access.mixin'
    _description = 'Vietnam Report Access Mixin'

    # The export controller only serves the models having this flag.
    _is_vn_report = True

    def _get_report_access_groups(self):
        """ Return the xml ids of the groups allowed to read the report;
        belonging to one of them is enough. The default matches the access
        rights of the report wizards.
        """
        return ['account.group_account_user']

    def _check_report_access(self, options=None):
        """ Raise an AccessError if the user is in none of the allowed groups,
        or if `options['company_id']` is not one of the user's companies.
        Normalize `options['company_id']` to an int.
        """
        if self.env.su:
            return
        groups = self._get_report_access_groups()
        if groups and not self.env.user.has_groups(','.join(groups)):
            raise AccessError(_("You are not allowed to view this report."))
        if options and options.get('company_id') is not None:
            try:
                company_id = int(options['company_id'])
            except (TypeError, ValueError):
                raise AccessError(_("Invalid company."))
            if company_id not in self.env.user.company_ids.ids:
                raise AccessError(_("You are not allowed to view the figures of this company."))
            options['company_id'] = company_id
