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
import openerp.exceptions

from datetime import datetime
import base64
import os

class LibrosElectronicosSii(osv.osv_memory):
    _name = "libros.electronicos.sii"
    
    _columns={
             'company_id' : fields.many2one('res.company', 'Compañia'),
             'period_id' : fields.many2one('account.period', 'Periodo'),                           
             'xml_name': fields.char('Nombre xml', size=200 ),
             'xml_file': fields.binary('XMLFILE'),
             'to_test': fields.boolean('Set de Prueba'),
             'type': fields.selection([
                            ('mensual','Mensual'),
                            #('especial','Especial'),
                            #('rectifica','Rectifica'), 
                            ], 'Tipo', required=True),              

             'type_send': fields.selection([
                            ('total','Total'),
                            ('final','Final'), 
                            ], 'Tipo', help="TOTAL =Información total del mes. Si no se incluye, se asume que es total.\n"+                                             
                                            "FINAL = Corresponde al último segmento"
            , required=True),              
             'type_book': fields.selection([
                            ('compra','Libro de Compra'),
                            ('venta','Libro de Venta'), 
                            ], 'Tipo de Libro', required=True)              
    }    
    def create_file(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[-1], context)
        invoice = self.pool.get('account.invoice')
        transmitter = self.pool.get('res.partner').browse(cr, uid, this.company_id.partner_id.id,)
        transmitter = invoice.limpiar_campos_emisor_xml(cr, uid, transmitter)
        invoice.validar_parametros_certificado(cr, uid, this.company_id)
        if this.type_book == 'compra':
            type = 'CV' + self.format_period(this.period_id).replace('-', '')
            name_file = 'LibroDeCompra_%s.xml' % datetime.now().strftime('%Y%m%d%H%M%S')
            sql_type = 'in%'
        else:
            type = 'VV' + self.format_period(this.period_id).replace('-', '')
            name_file = 'LibroDeVenta_%s.xml' % datetime.now().strftime('%Y%m%d%H%M%S')
            sql_type = 'out%'
        front_page = self.create_fromt_page(this, cr, uid, ids, transmitter, context)
        resume, invoices = self.create_resume_period(this, cr, uid, ids, sql_type, context)
        detail = False
        valid = False
        id_doc = self.format_period(this.period_id)
        if invoices and this.type_send == 'total':
            valid = True
            detail = self.create_detail(cr, uid, ids, invoices, this.type_book)
        try:
            path, file = self.get_file(front_page, resume, detail, valid, type, name_file, id_doc)            
        except:
            os.remove('/tmp/'+name_file)
            raise openerp.exceptions.Warning('Error al crear xml. Favor contactar al administrador del sistema')
        try:
            self.signature_book(cr, uid, ids, path, this, name_file)
        except:
            os.remove('/tmp/'+name_file)
            raise openerp.exceptions.Warning('Error al crear xml. Fallo Libreria Facturisa')
            
        mod_obj = self.pool.get('ir.model.data')
        res = mod_obj.get_object_reference(cr, uid, 'account_invoice_cl', 'libroelectronicosii_form')        
        return {
            'name': 'Libros Electronicos S.I.I',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res and res[1] or False],
            'res_model': 'libros.electronicos.sii',
            'context': "{}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': ids[0]  or False,##please replace record_id and provide the id of the record to be opened 
        }

    def signature_book(self, cr, uid, ids, path, this, name_file):
        par_firmador = self.pool.get('account.invoice').validar_parametros_firmador(cr, uid)
        data ={ 'path' : path,
                'cert': par_firmador.pathcertificado + this.company_id.export_filename, 
                'passwd' :this.company_id.p12pass if this.company_id.p12pass else '',
                'name' : '/tmp/f_' + name_file, 
                'pathbase' : par_firmador.pathbase
                }
        self.pool.get('firmador.firmador').firmar_libro_sii(cr, uid, ids, data, None)
        with open('/tmp/f_' + name_file, 'r') as myfile:
            b64data = base64.b64encode(myfile.read())            
            myfile.close()
        if not b64data:
            with open(path, 'r') as myfile:
                b64data = base64.b64encode(myfile.read())            
                myfile.close()            
        self.write(cr, uid, ids[0], {'xml_file': b64data, 'xml_name' : name_file })
        os.remove(path)
        os.remove('/tmp/f_'+name_file)
            
    def get_file(self, front, resume, detail, valid, type, name_file, id_doc):
        file = '<?xml version="1.0" encoding="ISO-8859-1"?>'
        file += '<LibroCompraVenta xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sii.cl/SiiDte LibroCV_v10.xsd" version="1.0">'
        file += '<EnvioLibro ID="ID%s">' % id_doc
        if valid:
            file += front
            file += resume
            file += detail
        else:
            file += front
        file += '<TmstFirma>'+ datetime.now().strftime('%Y-%m-%dT%H:%M:%S') +'</TmstFirma>'
        file += '</EnvioLibro>'
        file += '</LibroCompraVenta>'
        file.encode('ISO-8859-1')
        path = '/tmp/'+name_file
        vfile=open(path,'a+b')
        vfile.write(self.pool.get('account.invoice').special(file))                                
        vfile.close()        
        return path, file
                
    def create_fromt_page(self, this, cr, uid, ids, transmitter, context=None):
        invoice = self.pool.get('account.invoice')
        front_page = ''
        front_page += '<Caratula>'
        front_page += '<RutEmisorLibro>'+ invoice.validar_rut(this.company_id.vat) +'</RutEmisorLibro>'
        front_page += '<RutEnvia>'+ invoice.validar_rut(this.company_id.rutenvia) +'</RutEnvia>'
        front_page += '<PeriodoTributario>'+ self.format_period(this.period_id) +'</PeriodoTributario>'
        front_page += '<FchResol>'+ this.company_id.fecharesolucion +'</FchResol>'
        front_page += '<NroResol>'+ str(this.company_id.nroresolucion) +'</NroResol>'
        front_page += '<TipoOperacion>'+ this.type_book.upper() +'</TipoOperacion>'
        front_page += '<TipoLibro>'+this.type.upper() +'</TipoLibro>'
        front_page += '<TipoEnvio>'+this.type_send.upper() +'</TipoEnvio>'
        front_page += '</Caratula>'
        return front_page 

    def create_resume_period(self, this, cr, uid, ids, type, context=None):
        invoice_obj = self.pool.get('account.invoice')
        cr.execute("""select id from account_invoice 
                        where type like '%s' and state not in ('draft', 'cancel') 
                        and company_id = %d and period_id = %d and to_setest = %s
                     order by type""" % ( type, this.company_id.id, this.period_id.id, this.to_test))
        invoice_ids = map(lambda x:x[0], cr.fetchall())
        invoices = self.group_invoice_by_type(cr, uid, invoice_ids)        
        resume = ''
        resume += '<ResumenPeriodo>'
        for key in invoices.keys():
            totales, tax_obj = self.calc_totals(cr, uid, invoices[key])                 
            resume +='<TotalesPeriodo>'
            resume +='<TpoDoc>'+ str(key) +'</TpoDoc>'
            resume +='<TotDoc>'+ str(len(invoices[key])) +'</TotDoc>'
            if totales['anulados'] >0:
                resume +='<TotAnulado>'+ str(totales['anulados']) +'</TotAnulado>'                            
            resume +='<TotMntExe>'+  self.format_amount_integer(totales['exento']) +'</TotMntExe>'
            resume +='<TotMntNeto>'+ self.format_amount_integer(totales['neto'] ) +'</TotMntNeto>'
            resume +='<TotMntIVA>'+  self.format_amount_integer(totales['iva'] ) +'</TotMntIVA>'     
            if totales['no_recaudable']:
                for key_rec in totales['no_recaudable'].keys():
                    resume +='<TotIVANoRec>'
                    resume +='<CodIVANoRec>'+str(key_rec)+'</CodIVANoRec>'
                    resume +='<TotOpIVANoRec>'+str(totales['no_recaudable'][key_rec]['qty'])+'</TotOpIVANoRec>'
                    resume +='<TotMntIVANoRec>'+self.format_amount_integer(totales['no_recaudable'][key_rec]['monto']) +'</TotMntIVANoRec>'
                    resume +='</TotIVANoRec>'                   
            resume +='<TotMntTotal>'+ self.format_amount_integer(totales['total']) +'</TotMntTotal>'
            if totales['otros_imp']:
                for key_rec in totales['otros_imp'].keys():
                    resume +='<TotOtrosImp>'
                    resume +='<CodImp>'+str(key_rec)+'</CodImp>'
                    resume +='<TotMntImp>'+ self.format_amount_integer(totales['otros_imp'][key_rec]['monto']) +'</TotMntImp>'
                    resume +='</TotOtrosImp>'
            resume +='</TotalesPeriodo>'
        resume += '</ResumenPeriodo>'
        return resume, invoices

    def format_amount_integer(self, amount):        
        return str(int(round(amount)))

    def create_detail(self, cr, uid, ids, invoices, type):
        inv_obj = self.pool.get('account.invoice')
        detail = ''
        for key in invoices.keys():
            for inv in invoices[key]:
                totales, tax_obj = self.calc_totals(cr, uid, [inv])
                detail += '<Detalle>'
                detail += '<TpoDoc>'+ inv.journal_id.code_sii +'</TpoDoc>'
                if type == 'compra':
                    detail += '<NroDoc>'+ inv_obj.limpiar_campo_slash(inv.supplier_invoice_number) +'</NroDoc>'
                else:                    
                    detail += '<NroDoc>'+ inv_obj.limpiar_campo_slash(inv.number) +'</NroDoc>'

                if totales['anulados'] >0:
                    detail +='<Anulado>A</Anulado>'
                    detail +='</Detalle>'
                    continue 
                impuesto_obj = inv_obj.buscar_impuesto_en_factura(cr, uid, inv, False)
                if impuesto_obj:
                    detail += '<TpoImp>'+ impuesto_obj.type_tax_sii +'</TpoImp>'
                    detail += '<TasaImp>'+ "{0:.2f}".format(impuesto_obj.amount * 100) +'</TasaImp>'
                else:
                    detail += '<TasaImp>'+str(0)+'</TasaImp>'
                detail += '<FchDoc>'+ inv.date_invoice +'</FchDoc>'
                detail += '<RUTDoc>'+ inv_obj.validar_rut(inv.partner_id.vat) +'</RUTDoc>'
                detail += '<RznSoc>'+ inv_obj.xmlescape(inv.partner_id.name) +'</RznSoc>'
                detail += '<MntExe>'+ self.format_amount_integer(totales['exento']) +'</MntExe>'
                detail += '<MntNeto>'+ self.format_amount_integer(totales['neto']) +'</MntNeto>'
                
                if totales['no_recaudable']:
                    for key_rec in totales['no_recaudable'].keys():
                        detail += '<IVANoRec>'
                        detail += '<CodIVANoRec>'+str(key_rec)+'</CodIVANoRec>'
                        detail += '<MntIVANoRec>'+ self.format_amount_integer(totales['no_recaudable'][key_rec]['monto'])+'</MntIVANoRec>'
                        detail += '</IVANoRec>' 
                elif totales['otros_imp']:
                    for key_rec in totales['otros_imp'].keys():
                        detail += '<OtrosImp>'
                        detail += '<CodImp>'+ str(key_rec)+'</CodImp>'
                        detail += '<TasaImp>'+ "{0:.2f}".format(tax_obj.amount * 100) +'</TasaImp>'
                        detail += '<MntImp>'+ self.format_amount_integer(totales['otros_imp'][key_rec]['monto']) +'</MntImp>'
                        detail += '</OtrosImp>'
                else:
                    detail += '<MntIVA>'+ self.format_amount_integer(totales['iva']) +'</MntIVA>'
                detail += '<MntTotal>'+ self.format_amount_integer(totales['total']) +'</MntTotal>'
                detail += '</Detalle>'
        return detail
        
    def format_period(self, period):
        date = datetime.strptime(period.date_start,'%Y-%m-%d')        
        return '{0}-{1}'.format(date.year, date.strftime('%m'))
    
    def group_invoice_by_type(self, cr, uid, invoice_ids):
        invoices = {}
        for invoice in self.pool.get('account.invoice').browse(cr, uid, invoice_ids):
            if invoice.journal_id.code_sii:
                if invoice.journal_id.code_sii in invoices.keys(): 
                    invoices[invoice.journal_id.code_sii].append(invoice)
                else:
                    invoices[invoice.journal_id.code_sii] = [invoice]
            else:
                raise openerp.exceptions.Warning('Error al crear xml. Favor ingresar campo Codigo sii en el diario %s' % invoice.journal_id.name)
        return invoices
        
    def calc_totals(self, cr, uid, invoices):
        totales = {'neto' : 0, 'iva' : 0, 'exento' : 0, 'total' : 0 ,
                    'no_recaudable' : {}, 'otros_imp': {},'anulados': 0
                   }
        tax_ret = False        
        tax_obj =self.pool.get('account.tax')

        for invoice in invoices:
            lno_rec, lotros = 0,0
            if invoice.state == 'nula':
                totales['anulados'] += 1
                continue
            totales['total'] += invoice.amount_total
            totales['iva'] += invoice.amount_tax
            totales['neto'] +=  invoice.amount_untaxed
            
            for line in invoice.invoice_line:
                if not line.invoice_line_tax_id:
                    totales['exento'] += line.price_subtotal
            for line_tax in invoice.tax_line:                                
                name = line_tax.name[line_tax.name.find('-')+1:].strip()                
                tax = self.get_tax_invoice(cr, uid, name, line_tax)
                if tax:
                    tax = tax_obj.browse(cr, uid, tax[0])
                    tax_ret = tax
                    if not tax.type_sii:
                        raise openerp.exceptions.Warning('Error al crear xml. Favor ingresar campo Tipo sii en el impuesto %s' % tax.name)
                    if tax.type_sii == 'no_recuperable':
                        self.validate_code_rec_other(invoice.codtax_norec, 'Codigo impuesto no recaudable', invoice.number)
                        if invoice.codtax_norec in totales['no_recaudable'].keys():
                            totales['no_recaudable'][invoice.codtax_norec]['monto'] += line_tax.amount
                            totales['no_recaudable'][invoice.codtax_norec]['qty'] += 1
                        else:
                            totales['no_recaudable'][invoice.codtax_norec] = {'monto':line_tax.amount, 'qty': 1}
                        lno_rec += line_tax.amount
                    elif tax.type_sii == 'otro':
                        self.validate_code_rec_other(invoice.codtax_imprecargo, 'codigo impuesto', invoice.number)
                        if invoice.codtax_norec in totales['otros_imp'].keys():
                            totales['otros_imp'][invoice.codtax_imprecargo.code]['monto'] += line_tax.amount
                            totales['otros_imp'][invoice.codtax_imprecargo.code]['qty'] += 1
                        else:
                            totales['otros_imp'][invoice.codtax_imprecargo.code] = {'monto' : line_tax.amount, 'qty' : 1}
                        lotros += line_tax.amount
            if invoice.amount_tax:
                totales['iva'] -= lno_rec 
        return totales, tax_ret  

    def get_tax_invoice(self,cr ,uid, name, line_tax):
        tax_obj =self.pool.get('account.tax')        
        tax = tax_obj.search(cr , uid,[('name','=', name),('base_code_id','=', line_tax.base_code_id.id)])
        if not tax:
            sql = "select src from ir_translation where value = '%s'" % name
            cr.execute(sql)
            name = cr.fetchone()
            if name and name[0] is not None:
                tax = tax_obj.search(cr , uid,[('name','=', name[0]),('base_code_id','=', line_tax.base_code_id.id)])
        return tax

    def validate_code_rec_other(self, code, type, number):
        if not code:
            raise openerp.exceptions.Warning('Error al crear xml. Favor ingresar campo %s en Factura %s' % (type, number))        

    def send_file(self, cr, uid, ids ,context=None):
        this = self.browse(cr, uid ,ids[-1], context)
        if this.xml_file:
            par_firmador = self.pool.get('account.invoice').validar_parametros_firmador(cr, uid)
            path = '/tmp/send_' + this.xml_name
            vfile = open(path,'a+b')
            vfile.write( base64.decodestring(this.xml_file))
            vfile.close()
            data ={ 'path' : path,
                    'cert': par_firmador.pathcertificado + this.company_id.export_filename, 
                    'passwd' :this.company_id.p12pass if this.company_id.p12pass else '',
                    'name' : par_firmador.pathbase + '/out/resp_sii/resp_' + this.xml_name, 
                    'pathbase' : par_firmador.pathbase
                    }
            self.pool.get('firmador.firmador').enviar_libro_sii(cr, uid, ids, data, None)
        else:
            raise openerp.exceptions.Warning('Error al enviar xml. Favor primero generar el Libro') 
LibrosElectronicosSii()    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: