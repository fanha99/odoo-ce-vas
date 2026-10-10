from odoo import api, fields, models
from odoo.tools import split_every

COUNTERED_FIELDS = ('countered_aml_ids', 'countered_account_ids', 'countered_amt', 'countered_status')


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
        """ Number of entries matched by `_get_moves_domain`, as a preview. """
        for wizard in self:
            wizard.move_count = self.env['account.move'].search_count(wizard._get_moves_domain())

    def _get_moves_domain(self):
        """ Domain of the posted entries to process: company, optional journals
        and dates, and in 'missing' mode only the entries not fully countered.
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

        The counterpart fields of the batch are recomputed explicitly: on
        entries posted before the module was installed they hold the default
        of their column, which is wrong for the items with nothing to counter
        (they are 'fully' countered) and is not refreshed by creating
        counterparts on the other items.
        """
        moves._ctp_generate(regenerate=self.mode == 'all')

        lines = moves.line_ids
        for field_name in COUNTERED_FIELDS:
            self.env.add_to_compute(lines._fields[field_name], lines)
        self.env.add_to_compute(moves._fields['countered_status'], moves)
        self.env.flush_all()
        self.env.invalidate_all()

    def action_generate(self):
        """ Process the matching entries by batches of `BATCH_SIZE` and notify
        the user with the number of entries processed.

        Everything runs in the transaction of the request: either every entry
        is processed, or none.
        """
        self.ensure_one()
        Move = self.env['account.move']
        move_ids = Move.search(self._get_moves_domain(), order='id').ids
        for batch_ids in split_every(self.BATCH_SIZE, move_ids):
            self._generate_batch(Move.browse(batch_ids))

        remaining = Move.search_count([('id', 'in', move_ids), ('countered_status', '!=', 'fully')])
        message = self.env._("%(count)s journal entries processed.", count=len(move_ids))
        if remaining:
            message += " " + self.env._(
                "%(count)s of them are not fully countered: entries with negative amounts are not supported yet.",
                count=remaining,
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning' if remaining else 'success',
                'title': self.env._("Counterparts generated"),
                'message': message,
                'sticky': bool(remaining),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
