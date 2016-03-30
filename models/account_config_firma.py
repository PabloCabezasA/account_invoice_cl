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

class account_config_firma(osv.osv):
    _name='account.config.firma'
    _columns={
             'pathbase': fields.char("Path base", help='Ruta a la libreria ej: /home/openerp/lfubu14_64', size=250),
             'pathfolio': fields.char("Path folios", help='Ruta a los folios ej: /home/openerp/caf/', size=250),
             'pathcertificado': fields.char("Path Certificados", help='Ruta a los certificados ej: /home/openerp/certificados/', size=250),             
             'type_send': fields.selection([
                        ('firmar','Firmar'),
                        ('firmar_enviar','Firmado e envio'), 
                        ], 'Tipo de Envio'),              
    }    
account_config_firma()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:#