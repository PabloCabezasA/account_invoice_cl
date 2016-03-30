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
from lxml import etree
import openerp.addons.decimal_precision as dp
import openerp.exceptions

from openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv, orm
from openerp.tools.translate import _

class account_invoice_dte(osv.osv):
    
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
            for line in invoice.tax_line:
                res[invoice.id]['amount_tax'] += line.amount
            res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']
        return res


    def _get_currency(self, cr, uid, context=None):
        res = False
        journal_id = self._get_journal(cr, uid, context=context)
        if journal_id:
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
            res = journal.currency and journal.currency.id or journal.company_id.currency_id.id
        return res


    def _get_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('type', 'out_invoice')

    def _get_reference_type(self, cr, uid, context=None):
        return [('none', _('Free Reference'))]

    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        """Function of the field residua. It computes the residual amount (balance) for each invoice"""
        if context is None:
            context = {}
        ctx = context.copy()
        result = {}
        currency_obj = self.pool.get('res.currency')
        for invoice in self.browse(cr, uid, ids, context=context):
            nb_inv_in_partial_rec = max_invoice_id = 0
            result[invoice.id] = 0.0
            if invoice.move_id:
                print invoice.move_id.line_id
                for aml in invoice.move_id.line_id:
                    if aml.account_id.type in ('receivable','payable'):
                    
                        if aml.currency_id and aml.currency_id.id == invoice.currency_id.id:
                            result[invoice.id] += aml.amount_residual_currency
                        else:
                            ctx['date'] = aml.date
                            result[invoice.id] += currency_obj.compute(cr, uid, aml.company_id.currency_id.id, invoice.currency_id.id, aml.amount_residual, context=ctx)

                        if aml.reconcile_partial_id.line_partial_ids:
                            #we check if the invoice is partially reconciled and if there are other invoices
                            #involved in this partial reconciliation (and we sum these invoices)
                            for line in aml.reconcile_partial_id.line_partial_ids:
                                if line.invoice:
                                    nb_inv_in_partial_rec += 1
                                    #store the max invoice id as for this invoice we will make a balance instead of a simple division
                                    max_invoice_id = max(max_invoice_id, line.invoice.id)
            if nb_inv_in_partial_rec:
                #if there are several invoices in a partial reconciliation, we split the residual by the number
                #of invoice to have a sum of residual amounts that matches the partner balance
                new_value = currency_obj.round(cr, uid, invoice.currency_id, result[invoice.id] / nb_inv_in_partial_rec)
                if invoice.id == max_invoice_id:
                    #if it's the last the invoice of the bunch of invoices partially reconciled together, we make a
                    #balance to avoid rounding errors
                    result[invoice.id] = result[invoice.id] - ((nb_inv_in_partial_rec - 1) * new_value)
                else:
                    result[invoice.id] = new_value

            #prevent the residual amount on the invoice to be less than 0
            result[invoice.id] = max(result[invoice.id], 0.0)            
        return result

    # Give Journal Items related to the payment reconciled to this invoice
    # Return ids of partial and total payments related to the selected invoices
    def _get_lines(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            id = invoice.id
            res[id] = []
            if not invoice.move_id:
                continue
            data_lines = [x for x in invoice.move_id.line_id if x.account_id.id == invoice.account_id.id]
            partial_ids = []
            for line in data_lines:
                ids_line = []
                if line.reconcile_id:
                    ids_line = line.reconcile_id.line_id
                elif line.reconcile_partial_id:
                    ids_line = line.reconcile_partial_id.line_partial_ids
                l = map(lambda x: x.id, ids_line)
                partial_ids.append(line.id)
                res[id] =[x for x in l if x <> line.id and x not in partial_ids]
        return res

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line.dte').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax.dte').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    def _compute_lines(self, cr, uid, ids, name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            src = []
            lines = []
            if invoice.move_id:
                for m in invoice.move_id.line_id:
                    temp_lines = []
                    if m.reconcile_id:
                        temp_lines = map(lambda x: x.id, m.reconcile_id.line_id)
                    elif m.reconcile_partial_id:
                        temp_lines = map(lambda x: x.id, m.reconcile_partial_id.line_partial_ids)                    
                    lines += [x for x in temp_lines if x not in lines]
                    src.append(m.id)            
            lines = filter(lambda x: x not in src, lines)
            result[invoice.id] = lines        
        return result

    _name = "account.invoice.dte"        
    _order = "id desc"
    
    _columns = {
        'name': fields.char('descripcion', size=64, select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'origin': fields.char('Origen', size=64, help="Reference of the document that produced this invoice.", readonly=True, states={'draft':[('readonly',False)]}),
        'supplier_invoice_number': fields.char('N° factura proveedor', size=64, help="The reference of this invoice as provided by the supplier.", readonly=True, states={'draft':[('readonly',False)]}),
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
            ],'Type', readonly=True, select=True, change_default=True, track_visibility='always'),

        'number': fields.related('move_id','name', type='char', readonly=True, size=64, relation='account.move', store=True, string='Numero'),
        'internal_number': fields.char('Numero Factura', size=32, readonly=True, help="Unique number of the invoice, computed automatically when the invoice is created."),
        'reference': fields.char('Referencia Factura', size=64, help="The partner reference of this invoice."),
        'reference_type': fields.selection(_get_reference_type, 'Referencia Pago',
            required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'comment': fields.text('Informacion Adicional'),

        'state': fields.selection([
            ('draft','borrador'),                        
            ('repeat','repetida'),
            ('open','enviado'),            
            ('cancel','cancelado'),
            ],'Status', select=True, readonly=True, track_visibility='onchange',
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed Invoice. \
            \n* The \'Pro-forma\' when invoice is in Pro-forma status,invoice does not have an invoice number. \
            \n* The \'Open\' status is used when user create invoice,a invoice number is generated.Its in open status till user does not pay invoice. \
            \n* The \'Paid\' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled. \
            \n* The \'Cancelled\' status is used when user cancel invoice.'),
        'sent': fields.boolean('Sent', readonly=True, help="It indicates that the invoice has been sent."),
        'date_invoice': fields.date('Fecha Factura', readonly=True, states={'draft':[('readonly',False)]}, select=True, help="Keep empty to use the current date"),
        'date_due': fields.date('Fecha vencimiento', readonly=True, states={'draft':[('readonly',False)]}, select=True,
            help="If you use payment terms, the due date will be computed automatically at the generation "\
                "of accounting entries. The payment term may compute several due dates, for example 50% now and 50% in one month, but if you want to force a due date, make sure that the payment term is not set on the invoice. If you keep the payment term and the due date empty, it means direct payment."),
        'partner_id': fields.many2one('res.partner', 'Proveedor', change_default=True, readonly=True, required=True, states={'draft':[('readonly',False)]}, track_visibility='always'),
        'payment_term': fields.many2one('account.payment.term', 'Terminos de Pago',readonly=True, states={'draft':[('readonly',False)]},
            help="If you use payment terms, the due date will be computed automatically at the generation "\
                "of accounting entries. If you keep the payment term and the due date empty, it means direct payment. "\
                "The payment term may compute several due dates, for example 50% now, 50% in one month."),
        'period_id': fields.many2one('account.period', 'Forzar Periodo', domain=[('state','<>','done')], help="Keep empty to use the period of the validation(invoice) date.", readonly=True, states={'draft':[('readonly',False)]}),

        'account_id': fields.many2one('account.account', 'Cuenta', required=True, readonly=True, states={'draft':[('readonly',False)]}, help="The partner account used for this invoice."),
        'invoice_line': fields.one2many('account.invoice.line.dte', 'invoice_id', 'Lineas Factura', readonly=True, states={'draft':[('readonly',False)]}),
        
        
        'tax_line': fields.one2many('account.invoice.tax.dte', 'invoice_id', 'Lineas impuesto', readonly=True, states={'draft':[('readonly',False)]}),
        
        
        'move_id': fields.many2one('account.move', 'Movimiento', readonly=True, select=1, ondelete='restrict', help="Link to the automatically generated Journal Items."),
        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Subtotal', track_visibility='always',
            store={
                'account.invoice.dte': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax.dte': (_get_invoice_tax, None, 20),
                'account.invoice.line.dte': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='impuesto',
            store={
                'account.invoice.dte': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax.dte': (_get_invoice_tax, None, 20),
                'account.invoice.line.dte': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
                
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'account.invoice.dte': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax.dte': (_get_invoice_tax, None, 20),
                'account.invoice.line.dte': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'currency_id': fields.many2one('res.currency', 'Divisa', required=True, readonly=True, states={'draft':[('readonly',False)]}, track_visibility='always'),
        'journal_id': fields.many2one('account.journal', 'Diario', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.many2one('res.company', 'Compania', required=True, change_default=True, readonly=True, states={'draft':[('readonly',False)]}),
        'check_total': fields.float('Verificacion Total', digits_compute=dp.get_precision('Account'), readonly=True, states={'draft':[('readonly',False)]}),        
        'partner_bank_id': fields.many2one('res.partner.bank', 'Bank Account',
            help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Supplier Refund, otherwise a Partner bank account number.', readonly=True, states={'draft':[('readonly',False)]}),
        
        'move_lines':fields.function(_get_lines, type='many2many', relation='account.move.line', string='Lineas entrantes'),                
        'move_name': fields.char('Movimiento', size=64, readonly=True, states={'draft':[('readonly',False)]}),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True, track_visibility='onchange', states={'draft':[('readonly',False)]}),
        'fiscal_position': fields.many2one('account.fiscal.position', 'Posicion Fiscal', readonly=True, states={'draft':[('readonly',False)]})
    }
    _defaults = {
        'type': _get_type,
        'state': 'draft',
        'currency_id': _get_currency,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'account.invoice.dte', context=c),
        'reference_type': 'none',
        'check_total': 0.0,
        'internal_number': False,
        'user_id': lambda s, cr, u, c: u,
        'sent': False,
    }


    def create(self, cr, uid, data, context=None):
        id = super(account_invoice_dte, self).create(cr, uid, data, context)
        dte = self.browse(cr, uid, id, context)
        ids = self.search(cr, uid, [('partner_id','=',dte.partner_id.id),('journal_id','=',dte.journal_id.id),('supplier_invoice_number','=',dte.supplier_invoice_number),('id','!=',id)])
        if ids:
            self.write(cr, uid, id, {'state': 'repeat'})
        return id

    def validar_factura_existente(self, cr, uid, invoice):        
        max_amount_total = float(str("%d.99"% int(invoice['amount_total'])))
        max_amount_untaxed = float(str("%d.99"% int(invoice['amount_untaxed'])))             
        sql = """select id from account_invoice where 
              partner_id ={0} 
              and type ='in_invoice' 
              and amount_total >= {1}
              and amount_total <= {2} 
              and amount_untaxed >= {3}
              and amount_untaxed <= {4}
              and supplier_invoice_number = '{5}'
              order by id desc 
             """.format(invoice['partner_id'][0] , int(invoice['amount_total']),max_amount_total,int(invoice['amount_untaxed']),max_amount_untaxed,invoice['supplier_invoice_number'])
        cr.execute(sql)
        id_factura = cr.fetchall()
        if id_factura:
            id_factura = map(lambda x: x[0], id_factura)
            invoice_obj = self.pool.get('account.invoice').browse(cr, uid , list(id_factura))
            msj = 'Factura ya se encuentra registrada \n' 
            romper = False
            for inv in invoice_obj:
                if inv.state != 'draft':
                    msj += 'estado = (%s)' % inv.state
                    romper = True
            if romper:                
                activo_id = self.pool.get('account.invoice.dte.wz').create(cr,uid,{'invoice_id':invoice['id'],'name':msj})
                 # redisplay the record as a sales order
                view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_invoice_cl', 'invoice_supplier_dte_wz')
                view_id = view_ref and view_ref[1] or False,
                return{
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.invoice.dte.wz',
                    'res_id': activo_id,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id': view_id,
                    'target': 'new',
                    'nodestroy': True,
                }
        
                #raise openerp.exceptions.Warning(  )
            else: return False
        else:
            return False 


    def cancelar_factura_borrador(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids[0],{'state':'cancel'})
        return True

    def crear_factura_borrador(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        dte_line_obj = self.pool.get('account.invoice.line.dte')
        invoice_dte = self.read(cr,uid,ids[0])
        if not context.has_key('validar'):
            re = self.validar_factura_existente(cr, uid, invoice_dte)
            return re
        value = {'account_id' : invoice_dte['account_id'][0],'amount_tax':invoice_dte['amount_tax'],'amount_total':invoice_dte['amount_total'],'amount_untaxed':invoice_dte['amount_untaxed'],'comment':invoice_dte['comment']
                 ,'company_id':invoice_dte['company_id'][0],'currency_id':invoice_dte['currency_id'][0],'date_due':invoice_dte['date_due'],'date_invoice':invoice_dte['date_invoice'],'fiscal_position':invoice_dte['fiscal_position']
                 ,'journal_id':invoice_dte['journal_id'][0],'partner_id':invoice_dte['partner_id'][0],'state':'draft','origin':invoice_dte['supplier_invoice_number'],'type':invoice_dte['type'],'supplier_invoice_number':invoice_dte['supplier_invoice_number']
                 }
        inv_id = invoice_obj.create(cr,uid,value)
        for line_dte in invoice_dte['invoice_line']:
            line = dte_line_obj.read(cr,uid,line_dte)
            line['account_id'] = line['account_id'][0]
            line['invoice_id'] = inv_id
            line['company_id'] = line['company_id'][0]
            line['partner_id'] = line['partner_id'][0]
            line['invoice_line_tax_id'] = [(6, 0, line['invoice_line_tax_id'])]
            if line['product_id']:
                line['product_id'] = line['product_id'][0]
            del line['id']
            invoice_line_obj.create(cr,uid,line)
        self.write(cr,uid,ids[0],{'state':'open'})
        self.pool.get('account.invoice').button_reset_taxes(cr, uid, [inv_id], context)
        return True 


       
    def unlink(self, cr, uid, ids, context=None): 
        if context is None:
            context = {}
        invoices = self.read(cr, uid, ids, ['state','internal_number'], context=context)
        unlink_ids = []

        for t in invoices:
            if t['state'] not in ('draft', 'cancel'):
                raise openerp.exceptions.Warning(_('You cannot delete an invoice which is not draft or cancelled. You should refund it instead.'))
            elif t['internal_number']:
                raise openerp.exceptions.Warning(_('You cannot delete an invoice after it has been validated (and received a number).  You can set it back to "Draft" state and modify its content, then re-confirm it.'))
            else:
                unlink_ids.append(t['id'])

        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True


    def onchange_invoice_line(self, cr, uid, ids, lines):
        return {}

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({
            'state':'draft',
            'number':False,
            'move_id':False,
            'move_name':False,
            'internal_number': False,
            'period_id': False,
            'sent': False,
        })
        if 'date_invoice' not in default:
            default.update({
                'date_invoice':False
            })
        if 'date_due' not in default:
            default.update({
                'date_due':False
            })
        return super(account_invoice_dte, self).copy(cr, uid, id, default, context)


    def button_reset_taxes(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ait_obj = self.pool.get('account.invoice.tax.dte')
        for id in ids:
            cr.execute("DELETE FROM account_invoice_tax_dte WHERE invoice_id=%s AND manual is False", (id,))
            partner = self.browse(cr, uid, id, context=ctx).partner_id
            if partner.lang:
                ctx.update({'lang': partner.lang})
            for taxe in ait_obj.compute(cr, uid, id, context=ctx).values():
                ait_obj.create(cr, uid, taxe)
        # Update the stored value (fields.function), so we write to trigger recompute
        self.pool.get('account.invoice.dte').write(cr, uid, ids, {'invoice_line':[]}, context=ctx)
        return True

    def _convert_ref(self, cr, uid, ref):
        return (ref or '').replace('/','')


    def invoice_validate(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state':'open'}, context=context)
        return True


    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        types = {
                'out_invoice': _('Invoice'),
                'in_invoice': _('Supplier Invoice'),
                'out_refund': _('Refund'),
                'in_refund': _('Supplier Refund'),
                }
        return [(r['id'], '%s %s' % (r['number'] or types[r['type']], r['name'] or '')) for r in self.read(cr, uid, ids, ['type', 'number', 'name'], context, load='_classic_write')]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('number','=',name)] + args, limit=limit, context=context)
        if not ids:
            ids = self.search(cr, user, [('name',operator,name)] + args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context)

account_invoice_dte()

class account_invoice_line_dte(osv.osv):

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            price = line.price_unit * (1-(line.discount or 0.0)/100.0)
            taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
            res[line.id] = taxes['total']
            if line.invoice_id:
                cur = line.invoice_id.currency_id
                res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    def _price_unit_default(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('check_total', False):
            t = context['check_total']
            for l in context.get('invoice_line', {}):
                if isinstance(l, (list, tuple)) and len(l) >= 3 and l[2]:
                    tax_obj = self.pool.get('account.tax')
                    p = l[2].get('price_unit', 0) * (1-l[2].get('discount', 0)/100.0)
                    t = t - (p * l[2].get('quantity'))
                    taxes = l[2].get('invoice_line_tax_id')
                    if len(taxes[0]) >= 3 and taxes[0][2]:
                        taxes = tax_obj.browse(cr, uid, list(taxes[0][2]))
                        for tax in tax_obj.compute_all(cr, uid, taxes, p,l[2].get('quantity'), l[2].get('product_id', False), context.get('partner_id', False))['taxes']:
                            t = t - tax['amount']
            return t
        return 0

    _name = "account.invoice.line.dte"
    _description = "Invoice Line"
    _order = "invoice_id,sequence,id"
    _columns = {
        'name': fields.text('Descripcion', required=True),
        'origin': fields.char('Origen', size=256, help="Reference of the document that produced this invoice."),
        'sequence': fields.integer('Secuencia', help="Gives the sequence of this line when displaying the invoice."),
        'invoice_id': fields.many2one('account.invoice.dte', 'Referencia Factura', ondelete='cascade', select=True),
        'uos_id': fields.many2one('product.uom', 'Unidad de Medida', ondelete='set null', select=True),
        'product_id': fields.many2one('product.product', 'Producto', ondelete='set null', select=True),
        'account_id': fields.many2one('account.account', 'Cuenta', required=True, domain=[('type','<>','view'), ('type', '<>', 'closed')], help="The income or expense account related to the selected product."),
        'price_unit': fields.float('Precio Unitario', required=True, digits_compute= dp.get_precision('Product Price')),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', type="float",
            digits_compute= dp.get_precision('Account'), store=True),
        'quantity': fields.float('Quantity', digits_compute= dp.get_precision('Cantidad'), required=True),
        'discount': fields.float('Discount (%)', digits_compute= dp.get_precision('Descuento')),
        'invoice_line_tax_id': fields.many2many('account.tax', 'account_invoice_line_dte_tax', 'invoice_line_id', 'tax_id', 'Impuesto', domain=[('parent_id','=',False)]),
        'account_analytic_id':  fields.many2one('account.analytic.account', 'Cuenta Analitica'),
        'company_id': fields.related('invoice_id','company_id',type='many2one',relation='res.company',string='Compañia', store=True, readonly=True),
        'partner_id': fields.related('invoice_id','partner_id',type='many2one',relation='res.partner',string='Proveedor',store=True)
    }


    _defaults = {
        'quantity': 1,
        'discount': 0.0,
        'price_unit': _price_unit_default,
        'sequence': 10,
    }
    

    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = []
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id.id
        for line in inv.invoice_line:
            mres = self.move_line_get_item(cr, uid, line, context)
            if not mres:
                continue
            res.append(mres)
            tax_code_found= False
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id,
                    (line.price_unit * (1.0 - (line['discount'] or 0.0) / 100.0)),
                    line.quantity, line.product_id,
                    inv.partner_id)['taxes']:

                if inv.type in ('out_invoice', 'in_invoice'):
                    tax_code_id = tax['base_code_id']
                    tax_amount = line.price_subtotal * tax['base_sign']
                else:
                    tax_code_id = tax['ref_base_code_id']
                    tax_amount = line.price_subtotal * tax['ref_base_sign']

                if tax_code_found:
                    if not tax_code_id:
                        continue
                    res.append(self.move_line_get_item(cr, uid, line, context))
                    res[-1]['price'] = 0.0
                    res[-1]['account_analytic_id'] = False
                elif not tax_code_id:
                    continue
                tax_code_found = True

                res[-1]['tax_code_id'] = tax_code_id
                res[-1]['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, tax_amount, context={'date': inv.date_invoice})
        return res

    def move_line_get_item(self, cr, uid, line, context=None):
        return {
            'type':'src',
            'name': line.name.split('\n')[0][:64],
            'price_unit':line.price_unit,
            'quantity':line.quantity,
            'price':line.price_subtotal,
            'account_id':line.account_id.id,
            'product_id':line.product_id.id,
            'uos_id':line.uos_id.id,
            'account_analytic_id':line.account_analytic_id.id,
            'taxes':line.invoice_line_tax_id,
        }
    #
    # Set the tax field according to the account and the fiscal position
    #
    def onchange_account_id(self, cr, uid, ids, product_id, partner_id, inv_type, fposition_id, account_id):
        if not account_id:
            return {}
        unique_tax_ids = []
        fpos = fposition_id and self.pool.get('account.fiscal.position').browse(cr, uid, fposition_id) or False
        account = self.pool.get('account.account').browse(cr, uid, account_id)
        if not product_id:
            taxes = account.tax_ids
            unique_tax_ids = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes)
        else:
            product_change_result = self.product_id_change(cr, uid, ids, product_id, False, type=inv_type,
                partner_id=partner_id, fposition_id=fposition_id,
                company_id=account.company_id.id)
            if product_change_result and 'value' in product_change_result and 'invoice_line_tax_id' in product_change_result['value']:
                unique_tax_ids = product_change_result['value']['invoice_line_tax_id']
        return {'value':{'invoice_line_tax_id': unique_tax_ids}}


account_invoice_line_dte()

class account_invoice_tax_dte(osv.osv):
    _name = "account.invoice.tax.dte"
    _description = "Invoice Tax dte"

    def _count_factor(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice_tax in self.browse(cr, uid, ids, context=context):
            res[invoice_tax.id] = {
                'factor_base': 1.0,
                'factor_tax': 1.0,
            }
            if invoice_tax.amount <> 0.0:
                factor_tax = invoice_tax.tax_amount / invoice_tax.amount
                res[invoice_tax.id]['factor_tax'] = factor_tax

            if invoice_tax.base <> 0.0:
                factor_base = invoice_tax.base_amount / invoice_tax.base
                res[invoice_tax.id]['factor_base'] = factor_base

        return res

    _columns = {
        'invoice_id': fields.many2one('account.invoice.dte', 'Linea Factura', ondelete='cascade', select=True),
        'name': fields.char('Nombre', size=64, required=True),
        'account_id': fields.many2one('account.account', 'Cuenta', required=True, domain=[('type','<>','view'),('type','<>','income'), ('type', '<>', 'closed')]),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic account'),
        'base': fields.float('Base', digits_compute=dp.get_precision('Account')),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'manual': fields.boolean('Manual'),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of invoice tax."),
        'base_code_id': fields.many2one('account.tax.code', 'Base Code', help="The account basis of the tax declaration."),
        'base_amount': fields.float('Base Code Amount', digits_compute=dp.get_precision('Account')),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Code', help="The tax basis of the tax declaration."),
        'tax_amount': fields.float('Tax Code Amount', digits_compute=dp.get_precision('Account')),
        'company_id': fields.related('account_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'factor_base': fields.function(_count_factor, string='Multipication factor for Base code', type='float', multi="all"),
        'factor_tax': fields.function(_count_factor, string='Multipication factor Tax code', type='float', multi="all")
    }

    def base_change(self, cr, uid, ids, base, currency_id=False, company_id=False, date_invoice=False):
        cur_obj = self.pool.get('res.currency')
        company_obj = self.pool.get('res.company')
        company_currency = False
        factor = 1
        if ids:
            factor = self.read(cr, uid, ids[0], ['factor_base'])['factor_base']
        if company_id:
            company_currency = company_obj.read(cr, uid, [company_id], ['currency_id'])[0]['currency_id'][0]
        if currency_id and company_currency:
            base = cur_obj.compute(cr, uid, currency_id, company_currency, base*factor, context={'date': date_invoice or time.strftime('%Y-%m-%d')}, round=False)
        return {'value': {'base_amount':base}}

    def amount_change(self, cr, uid, ids, amount, currency_id=False, company_id=False, date_invoice=False):
        cur_obj = self.pool.get('res.currency')
        company_obj = self.pool.get('res.company')
        company_currency = False
        factor = 1
        if ids:
            factor = self.read(cr, uid, ids[0], ['factor_tax'])['factor_tax']
        if company_id:
            company_currency = company_obj.read(cr, uid, [company_id], ['currency_id'])[0]['currency_id'][0]
        if currency_id and company_currency:
            amount = cur_obj.compute(cr, uid, currency_id, company_currency, amount*factor, context={'date': date_invoice or time.strftime('%Y-%m-%d')}, round=False)
        return {'value': {'tax_amount': amount}}

    _order = 'sequence'
    _defaults = {
        'manual': 1,
        'base_amount': 0.0,
        'tax_amount': 0.0,
    }
    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice.dte').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id
        company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id.id
        for line in inv.invoice_line:
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, line.product_id, inv.partner_id)['taxes']:
                val={}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = cur_obj.round(cr, uid, cur, tax['price_unit'] * line['quantity'])

                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
        return tax_grouped

    def move_line_get(self, cr, uid, invoice_id):
        res = []
        cr.execute('SELECT * FROM account_invoice_tax_dte WHERE invoice_id=%s', (invoice_id,))
        for t in cr.dictfetchall():
            if not t['amount'] \
                    and not t['tax_code_id'] \
                    and not t['tax_amount']:
                continue
            res.append({
                'type':'tax',
                'name':t['name'],
                'price_unit': t['amount'],
                'quantity': 1,
                'price': t['amount'] or 0.0,
                'account_id': t['account_id'],
                'tax_code_id': t['tax_code_id'],
                'tax_amount': t['tax_amount'],
                'account_analytic_id': t['account_analytic_id'],
            })
        return res
account_invoice_tax_dte()    

class account_invoice_dte_wz(osv.osv_memory):
    _name = "account.invoice.dte.wz"
    _columns = {
        'invoice_id': fields.many2one('account.invoice.dte', 'Linea Factura'),
        'name': fields.text('Nombre', size=250, readonly=True),
    }
    
    def registrar_factura(self,cr,uid,ids,context = None):
        wz = self.browse(cr,uid,ids[0])
        context = {'validar':False}
        self.pool.get('account.invoice.dte').crear_factura_borrador(cr,uid,[wz.invoice_id.id],context)
        return True
account_invoice_dte_wz()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
