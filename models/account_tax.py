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

from openerp.osv import osv, fields

class account_tax(osv.osv):
    _inherit = 'account.tax'
    _columns = {
              'type_sii': fields.selection([
                        ('comun','Comun'),
                        ('no_recuperable','No Recuperable'),
                        ('otro','Otro') 
                        ], 'Tipo sii'),    
              'type_tax_sii': fields.selection([
                        ('1','IVA'),
                        ('2','Ley 18.211'),
                        ], 'Tipo sii'),    
}
    _defaults = {
        'type_sii' : 'comun',
        'type_tax_sii' : '1',
    }
            
account_tax()

class cod_recargo(osv.osv):
    _name = 'cod.recargo'
    _columns = {
              'name': fields.char('Codigo', size=250, required=True),
              'code': fields.integer('Descripcion', size=2, required=True),    
}
cod_recargo()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#