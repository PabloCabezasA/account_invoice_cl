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

from openerp.osv import fields, osv
import base64


class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
                'user_sii_mail': fields.boolean('Usuario correo SII'),
    }
res_users()

class res_partner(osv.osv):    
    _inherit = 'res.partner'
    _columns = {        
        'name_fantasy': fields.char('Nombre Fantasia', size=250),
        'giro': fields.char('Giro', size=80),
        'servicio_basicos' : fields.boolean('Servicio Basicos')
        
    }
    
res_partner()

class res_company(osv.osv):    
    _inherit = 'res.company'
    _columns = {        
        'acteco': fields.integer('Acteco', size=6),
        'p12pass': fields.char('Contraseña', size=50),
        'filep12': fields.binary('Ingrese Certificado'),
        'export_filename': fields.char('Nombre del Certificado', size=200),
        'nroresolucion': fields.integer('Numero resolucion', size=4),
        'fecharesolucion': fields.date('Fecha resolucion'),

        
                
    }
    
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
        

    def validar_parametros_firmador(self, cr, uid):
        context = {}
        acf_obj = self.pool.get('account.config.firma')
        for acf in acf_obj.browse(cr, uid, acf_obj.search(cr, uid, [], context)):
            return acf
        raise openerp.exceptions.Warning('Error al crear la factura. Favor crear parametros del firmador')

res_company()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#