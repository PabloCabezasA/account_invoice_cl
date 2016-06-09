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

from openerp import fields, models
import base64


class res_users(models.Model):
    _inherit = 'res.users'
    user_sii_mail = fields.Boolean('Usuario correo SII')

res_users()

class res_partner(models.Model):    
    _inherit = 'res.partner'
    name_fantasy = fields.Char('Nombre Fantasia', size=250)
    giro = fields.Char('Giro', size=80)
    servicio_basicos = fields.Boolean('Servicio Basicos')
        
    
res_partner()

class res_company(models.Model):    
    _inherit = 'res.company'
    acteco = fields.Integer('Acteco', size=6)
    p12pass = fields.Char('Contraseña', size=50)
    filep12 = fields.Binary('Ingrese Certificado')
    export_filename = fields.Char('Nombre del Certificado', size=200)
    nroresolucion = fields.Integer('Numero resolucion', size=4)
    fecharesolucion = fields.Date('Fecha resolucion')
    rutenvia = fields.Char('RUT Envia', size=32, help="Tax Identification Number. Check the box if this contact is subjected to taxes. Used by the some of the legal statements.")
                    
    def write(self, cr, uid, ids, args, context=None):
        res = super(res_company, self).write(cr, uid, ids, args, context)
        if args.has_key('filep12') and args['filep12']:
            if context is None:
                context = {}
                context['id_file'] = ids[0] 
            else:
                context['id_file'] = ids[0]
            self.crear_archivo_en_ruta(cr, uid, args, context)
        return res
    
    def create(self, cr, uid, data, context=None):
        res = super(res_company, self).create(cr, uid, data, context)
        if data.has_Key('filep12'):
            self.crear_archivo_en_ruta(cr, uid, data, context)
        return res
        
    def crear_archivo_en_ruta(self, cr, uid, data, context= None):
        if context is None:
            context = {}
        par_firma = self.validar_parametros_firmador(cr, uid)
        if context.has_key('id_file'):
            if data.has_key('export_filename'):
                fh = open(par_firma.pathcertificado + data['export_filename'], "wb")
            else:
                resp = self.browse(cr, uid, context['id_file'])
                fh = open(par_firma.pathcertificado + resp.export_filename, "wb")
        else:
            fh = open(par_firma.pathcertificado + data['export_filename'], "wb")
        fh.write(base64.b64decode(data['filep12']))
        fh.close()
        
    def check_vat_company(self, cr, uid, ids,  context=None):
        partnerObj= self.pool.get("res.partner")
        for company in self.browse(cr, uid, ids, context):
            if not company.rutenvia:
                continue
            vat_country, vat_number = partnerObj._split_vat(company.rutenvia)
            check_func = partnerObj.simple_vat_check
            if not check_func(cr, uid, vat_country, vat_number, context=context):
                return False
        return True

    def validar_parametros_firmador(self, cr, uid):
        context = {}
        acf_obj = self.pool.get('account.config.firma')
        for acf in acf_obj.browse(cr, uid, acf_obj.search(cr, uid, [], context)):
            return acf
        raise openerp.exceptions.Warning('Error al crear la factura. Favor crear parametros del firmador')

    _constraints = [(check_vat_company, "Rut Envia invalido", ["rutenvia"])]

res_company()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#