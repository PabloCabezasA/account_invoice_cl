# -*- coding: utf-8 -*-
from openerp import fields, api
from openerp.osv import osv
from openerp.exceptions import except_orm, Warning, RedirectWarning
import os
from xml.dom.minidom import parse,parseString
import base64
from datetime import datetime

class firmador_firmador(osv.osv_memory):
    _name = 'firmador.firmador'

    @api.model
    def firmar_libro_sii(self, data):
        cert = data['cert']
        xml =  data['path']
        passwd = data['passwd']
        set_xml = data['name']
        pathbase =  data['pathbase']
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_firma = os.system(pathbase + '/facturador/facturista.sh --firmar_p12 ' + xml+ ' ' +  cert + ' ' + passwd + ' > ' + set_xml)
        return set_xml 

    @api.model
    def enviar_libro_sii(self, data):
        cert = data['cert']
        xml =  data['path']
        passwd = data['passwd']
        set_xml = data['name']
        pathbase =  data['pathbase']
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_envio = os.system(pathbase + '/facturador/facturista.sh --enviar ' + xml+ ' ' +  set_xml + ' ' +  '"Servidor=maullin.sii.cl;Puerto=443;SSL=1;ArchivoP12=' + cert + ';ContrasenaP12=' + passwd + '"')
        if resp_envio != 0:
            raise Warning('Error al enviar xml.  Contactar administrador') 
        print resp_envio 
        return set_xml 
    
    @api.model
    def firmar_set_prueba_sii(self, data, context=None):
        cert = data['cert']
        xml =  data['path']
        passwd = data['passwd']
        set_xml = '/tmp/SET_%s.xml' % str( datetime.now().strftime('%Y-%m-%d') )
        pathbase =  data['pathbase']
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_firma = os.system(pathbase + '/facturador/facturista.sh --firmar_p12 ' + xml+ ' ' +  cert + ' ' + passwd + ' > ' + set_xml)
        return set_xml 
    
    @api.model
    def firmar_dte_prueba_sii(self, ids, data, context=None):
        rutaxmldte =data['rutaxmldte']
        rutacertpfx = data['rutacertpfx']
        contcertpxpfx = data['contcertpxpfx']
        rutacaf = data['rutacaf']
        fecharesolucion = data['fecharesolucion']
        nroresolucion = data['nroresolucion']
        rutenvio = data['rutenvio']
        rutenviosii = rutenvio
        pathbase = data['pathbase']
        mids =  data['document_id']
        modelo = data['modelo']
        midom=parse(rutaxmldte)
        tipodte = midom.getElementsByTagName("TipoDTE")[0].childNodes[0].data
        rutemisor =  midom.getElementsByTagName("RUTEmisor")[0].childNodes[0].data.replace('-','')
        foliodte = midom.getElementsByTagName("Folio")[0].childNodes[0].data
        idDocument = midom.getElementsByTagName("Documento")[0].attributes.get("ID").value
        pathxmlfirmado = pathbase + '/out/dte_setprueba/'
        name_file = 'xmlset' + rutemisor + tipodte + foliodte + '.xml'
        xmlfirmadosii = pathbase + '/out/dte_setprueba/'+ name_file
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_firma = os.system(pathbase + '/facturador/facturista.sh --firmar_p12 ' + rutaxmldte+ ' ' +  rutacertpfx + ' ' +   contcertpxpfx + ' "CAF='+ rutacaf + '" >' + xmlfirmadosii)
        if resp_firma != 0:
            self.guardar_vitacora(mids, modelo, {'state': 'Error', 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Fallo al firmar dte'}, context)
        self.guardar_dte_en_modelo(mids, xmlfirmadosii, modelo, name=name_file)
        self.guardar_vitacora(mids, modelo, {'state': 'Firma DTE SII OK', 'code_sii': str(tipodte), 'folio': str(foliodte),'observacion': 'Proceso de firma DTE'}, context)
        os.remove(rutaxmldte)        
        os.chdir(pathbase+'/facturador/')
        return xmlfirmadosii
    
    @api.model
    def firmar_enviar_sii(self, ids, data, context=None):
        rutaxmldte =data['rutaxmldte']
        rutacertpfx = data['rutacertpfx']
        contcertpxpfx = data['contcertpxpfx']
        rutacaf = data['rutacaf']
        fecharesolucion = data['fecharesolucion']
        nroresolucion = data['nroresolucion']
        rutenvio = data['rutenvio']
        rutenviosii = rutenvio
        pathbase = data['pathbase']
        mids =  data['document_id']
        modelo = data['modelo']
        midom=parse(rutaxmldte)
        tipodte = midom.getElementsByTagName("TipoDTE")[0].childNodes[0].data
        rutemisor =  midom.getElementsByTagName("RUTEmisor")[0].childNodes[0].data.replace('-','')
        foliodte = midom.getElementsByTagName("Folio")[0].childNodes[0].data
        idDocument = midom.getElementsByTagName("Documento")[0].attributes.get("ID").value
        pathxmlfirmado = pathbase + '/out/dte_sii/'
        xmlfirmadosii = pathbase + '/out/dte_sii/xmlfirsii' + rutemisor + tipodte + foliodte + '.xml'
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_firma = os.system(pathbase + '/facturador/facturista.sh --firmar_p12 ' + rutaxmldte+ ' ' +  rutacertpfx + ' ' +   contcertpxpfx + ' "CAF=' + rutacaf + ';FechaResolucion=' + fecharesolucion +';NumeroResolucion=' + nroresolucion + ';RUTenvio=' + rutenvio + ';RUTrecepcion=60803000-K" > ' + xmlfirmadosii)
        if resp_firma != 0:
            self.guardar_vitacora(mids, modelo, {'state': 'Error', 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Fallo al firmar dte'}, context)
        self.guardar_dte_en_modelo(mids, xmlfirmadosii, modelo)
        self.guardar_vitacora(mids, modelo, {'state': 'Firma DTE SII OK', 'code_sii': str(tipodte), 'folio': str(foliodte),'observacion': 'Proceso de firma DTE'}, context)
        respenviosii = pathbase + '/out/resp_sii/respsii' + rutemisor + tipodte + foliodte + '.txt'
        os.remove(rutaxmldte)        
        os.chdir(pathbase+'/facturador/')
        os.system('pwd')
        resp_envio = os.system(pathbase + '/facturador/facturista.sh --enviar ' + xmlfirmadosii + ' ' + respenviosii   + ' ' +  '"Servidor=maullin.sii.cl;Puerto=443;SSL=1;ArchivoP12=' + rutacertpfx + ';ContrasenaP12=' + contcertpxpfx + '"')
        if resp_envio != 0:
            self.guardar_vitacora(mids, modelo, {'state': 'Error', 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Fallo al enviar dte a SII'}, context)
        else:
            mirespuestasii = open(respenviosii,'r')
            datosrespuestasii = mirespuestasii.read()
            inicioxmlrespuesta = datosrespuestasii.find('<?xml version="1.0"?>')
            textoxmlrespuestasii =     datosrespuestasii[inicioxmlrespuesta:]
            midomresp=parseString(textoxmlrespuestasii)
            timestamp = midomresp.getElementsByTagName("TIMESTAMP")[0].firstChild.nodeValue
            status = midomresp.getElementsByTagName("STATUS")[0].firstChild.nodeValue
            trackid = midomresp.getElementsByTagName("TRACKID")[0].firstChild.nodeValue
            self.guardar_vitacora(mids, modelo, {'state': str(status), 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Upload DTE correcto'}, context)
            self.env[modelo].browse(mids).write({'trackid' : trackid})
        return xmlfirmadosii

    @api.model
    def fimar_cliente(self, ids, data, context=None):
        rutaxmldte =data['rutaxmldte']
        rutacertpfx = data['rutacertpfx']
        contcertpxpfx = data['contcertpxpfx']
        rutacaf = data['rutacaf']
        fecharesolucion = data['fecharesolucion']
        nroresolucion = data['nroresolucion']
        rutenvio = data['rutenvio']
        rutenviosii = rutenvio
        pathbase = data['pathbase']
        mids =  data['document_id']
        modelo = data['modelo']
        midom=parse(rutaxmldte)
        tipodte = midom.getElementsByTagName("TipoDTE")[0].childNodes[0].data
        rutemisor =  midom.getElementsByTagName("RUTEmisor")[0].childNodes[0].data.replace('-','')
        foliodte = midom.getElementsByTagName("Folio")[0].childNodes[0].data
        idDocument = midom.getElementsByTagName("Documento")[0].attributes.get("ID").value
        pathxmlfirmado = pathbase + '/out/dte_otros/'
        xmlfirmadosii = pathbase + '/out/dte_otros/xmlfiroc' + rutemisor + tipodte + foliodte + '.xml'
        print xmlfirmadosii
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_firma = os.system( pathbase + '/facturador/facturista.sh --firmar_p12 ' + rutaxmldte+ ' ' +  rutacertpfx + ' ' +   contcertpxpfx + ' "CAF=' + rutacaf + ';FechaResolucion=' + fecharesolucion +';NumeroResolucion=' + str(nroresolucion) + ';RUTenvio=' + rutenvio + '" > ' + xmlfirmadosii
        )
        print 'respuesta firma'
        print resp_firma
        if resp_firma != 0:
            self.guardar_vitacora(mids, modelo, {'state': 'Error', 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Fallo al firmar dte'}, context)
        self.guardar_dte_en_modelo(mids, xmlfirmadosii, modelo)
        self.guardar_vitacora(mids, modelo, {'state': 'Firma DTE SII OK', 'code_sii': str(tipodte), 'folio': str(foliodte),'observacion': 'Proceso de firma DTE'}, context)
        midom=parse(xmlfirmadosii)
        elements = midom.getElementsByTagName("TED")
        respuesta = {}
        respuesta['respuesta'] = elements[0].toxml().replace('\n','').replace('\t','')
        respuesta['signed_path'] = xmlfirmadosii
        print respuesta
        os.remove(rutaxmldte)        
        return respuesta
 
    @api.model    
    def guardar_dte_en_modelo(self, ids, archivo, modelo, name = None):
        print 'guardando'
        b64data = ''
        if name is None:
            name = 'factura_%s.xml' % str(datetime.now().strftime('%Y%m%d%H%M%S'))
        try:
            with open(archivo, 'r') as myfile:
                b64data = base64.b64encode(myfile.read())
                myfile.close()
            print b64data
            self.env[modelo].browse(ids).write({'xml_file': b64data, 'export_filename' : name })
        except:
            print 'fallo al guardar archivo'

    @api.model
    def guardar_vitacora(self, ids, modelo, data, context=None):
        if modelo == 'account.invoice':
            data['invoice'] = ids
        elif modelo == 'stock.picking.out':
            data['picking_out_id'] = ids
        elif modelo == 'stock.picking.in':
            data['picking_out_in'] = ids
        self.env['account.invoice.emitidos'].create(data)
        return True
    