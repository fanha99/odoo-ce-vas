from odoo.tools.sql import column_exists

from . import models
from . import wizard


def _pre_init_counterpart(env):
    """ Create the stored status/amount columns with a constant default.

    Adding a column with a DEFAULT is instantaneous in PostgreSQL, whereas
    letting the ORM compute the new stored fields would load every existing
    journal item.  Existing entries start as "not countered"; the generator
    wizard fills them in afterwards.
    """
    cr = env.cr
    if not column_exists(cr, 'account_move_line', 'countered_status'):
        cr.execute("""
            ALTER TABLE account_move_line
                ADD COLUMN countered_status varchar DEFAULT 'none',
                ADD COLUMN countered_amt numeric DEFAULT 0
        """)
    if not column_exists(cr, 'account_move', 'countered_status'):
        cr.execute("ALTER TABLE account_move ADD COLUMN countered_status varchar DEFAULT 'none'")
