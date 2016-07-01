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
from lxml import objectify
import openerp
import base64

class account_invoice_folios(osv.osv):
	_name = 'account.invoice.folios'
	_columns = {
		'code_sii': fields.selection([
                            ('33','Facturación Eletrónica'),
                            ('34','Factura No Afecta o Exenta Electrónica'), 
                            ('43','Liquidación-Factura Electrónica'), 
                            ('46','Factura de Compra Electrónica'), 
                            ('52','Guía de Despacho Electrónica'),
                            ('56','Nota de Débito Electrónica'), 
                            ('61','Nota de Crédito Electrónica'),
                            ('110','Factura de Exportación'),
                            ('111','Nota de Débito de Exportación'),
                            ('112','Nota de Crédito de Exportación')
                            ], 'Codigo SII Chile'),
		'folio_start': fields.integer('Inicio Folio'),
		'folio_end': fields.integer('Termino Folio'),
		'date_approve': fields.date('Fecha Aprobación'),
		'state_folio': fields.selection([
										('1','Emitidos'),
			                            ('2','Actual'), 
			                            ('3','Disponibles'),
			                            ], 'Estados', ),
		'xml_folio': fields.binary('Ingrese Folios', filters='*.xml'),
		'export_filename': fields.char('Nombre del Folio', size=200), #Nombre Factura Firmada para rescate
		'company_id': fields.many2one('res.company', 'Compañia'),

    }
	
	def create(self, cr, uid, data, context=None):
		xml = objectify.fromstring(base64.b64decode(data['xml_folio']))
		values = ({
                    'code_sii': str(xml.CAF.DA.TD),
                    'folio_start': xml.CAF.DA.RNG.D,
                    'folio_end': xml.CAF.DA.RNG.H,
                    'date_approve': xml.CAF.DA.FA,
                    'state_folio': '3',
        			'xml_folio': data['xml_folio'],
                    'export_filename' : data['export_filename'],
					'company_id' : data['company_id'],

        })		
		reg = super(account_invoice_folios, self).create(cr, uid, values, context=context)
		self.crear_archivo_en_ruta(cr, uid, data, context)
		return reg
	
	def crear_archivo_en_ruta(self, cr, uid, data, context= None):
		par_firma = self.validar_parametros_firmador(cr, uid)
		fh = open(par_firma.pathfolio + data['export_filename'], "wb")
		fh.write(base64.b64decode(data['xml_folio']))
		fh.close()
		

	def validar_parametros_firmador(self, cr, uid):
		context = {}
		acf_obj = self.pool.get('account.config.firma')
		for acf in acf_obj.browse(cr, uid, acf_obj.search(cr, uid, [], context)):
			return acf
		raise openerp.exceptions.Warning('Error al crear la factura. Favor crear parametros del firmador')


	_sql_constraints = {
		('export_filename_uniq', 'unique(export_filename)', 'Archivo ya registrado')
	}
		
account_invoice_folios()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: