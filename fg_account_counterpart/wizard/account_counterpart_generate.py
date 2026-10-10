from odoo import api, fields, models


class AccountCounterpartGenerate(models.TransientModel):
    _name = 'account.counterpart.generate'
    _description = "Counterparts Generator"

    BATCH_SIZE = 1000   # journal entries processed per batch

    company_id = fields.Many2one(
        comodel_name='res.company', required=True, readonly=True,
        default=lambda self: self.env.company,
    )
    mode = fields.Selection(
        selection=[
            ('missing', "Generate missing counterparts"),
            ('all', "Regenerate all counterparts"),
        ],
        string="Operation", required=True, default='missing',
    )
    journal_ids = fields.Many2many(
        comodel_name='account.journal', string="Journals",
        check_company=True,
        help="Leave empty to process the entries of every journal.",
    )
    date_from = fields.Date(string="From")
    date_to = fields.Date(string="To")
    move_count = fields.Integer(string="Journal Entries to Process", compute='_compute_move_count')

    @api.depends('company_id', 'mode', 'journal_ids', 'date_from', 'date_to')
    def _compute_move_count(self):
        """ Number of entries matched by `_get_moves_domain`, as a preview.

        TODO(phase 5)
        """
        for wizard in self:
            wizard.move_count = self.env['account.move'].search_count(wizard._get_moves_domain())

    def _get_moves_domain(self):
        """ Domain of the posted entries to process: company, optional journals
        and dates, and in 'missing' mode only the entries not fully countered.

        TODO(phase 5)
        """
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id), ('state', '=', 'posted')]
        if self.journal_ids:
            domain.append(('journal_id', 'in', self.journal_ids.ids))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.mode == 'missing':
            domain.append(('countered_status', '!=', 'fully'))
        return domain

    def _generate_batch(self, moves):
        """ Generate the counterparts of one batch of entries, then flush and
        invalidate the cache to keep memory flat.

        TODO(phase 5)
        """
        moves._ctp_generate(regenerate=self.mode == 'all')

    def action_generate(self):
        """ Process the matching entries by batches of `BATCH_SIZE` and notify
        the user with the number of entries processed.

        TODO(phase 5)
        """
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
