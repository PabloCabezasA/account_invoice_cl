# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp.report import report_sxw
from openerp import pooler

def titlize(journal_name):
    words = journal_name.split()
    while words.pop() != 'journal':
        continue
    return ' '.join(words)

class order(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(order, self).__init__(cr, uid, name, context=context)

        user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid, context=context)
        partner = user.company_id.partner_id

        self.localcontext.update({
            'time': time,
            'disc': self.discount,
            'net': self.netamount,
            'get_journal_amt': self._get_journal_amt,
            'address': partner or False,
            'titlize': titlize,
            '_formato_numero': self._formato_numero,
            '_rut_emi' : self._rut_emi
        })

    def netamount(self, order_line_id):
        sql = 'select (qty*price_unit) as net_price from pos_order_line where id = %s'
        self.cr.execute(sql, (order_line_id,))
        res = self.cr.fetchone()
        return res[0]

    def discount(self, order_id):
        sql = 'select discount, price_unit, qty from pos_order_line where order_id = %s '
        self.cr.execute(sql, (order_id,))
        res = self.cr.fetchall()
        dsum = 0
        for line in res:
            if line[0] != 0:
                dsum = dsum + (line[2] * (line[0] * line[1] / 100))
        return dsum

    def _get_journal_amt(self, order_id):
        data = {}
        sql = """ select aj.name,absl.amount as amt from account_bank_statement as abs
                        LEFT JOIN account_bank_statement_line as absl ON abs.id = absl.statement_id
                        LEFT JOIN account_journal as aj ON aj.id = abs.journal_id
                        WHERE absl.pos_statement_id =%d""" % (order_id)
        self.cr.execute(sql)
        data = self.cr.dictfetchall()
        return data
    
    def _formato_numero(self, numero):
        while '/' in numero:
            numero=numero[numero.index('/')+1:]
            print numero
        return numero
    

    def _rut_emi(self, rut):
        if not rut:
            rut = ''
        rut = rut.lower().replace("cl", "")
        l = rut.__len__()
        if rut:
            vat = str(rut[l-l:l-7] + '.' + rut[l-7:l-4] + '.' + rut[l-4:l-1] + '-' + rut[l-1:l])
            return vat
        return rut
try:
    report_sxw.report_sxw('report.pos.receipt_elect', 'pos.order', 'addons/account_invoice_cl/report/pos_receipt.rml', parser=order, header=False)
except:
    print 'existe'
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: