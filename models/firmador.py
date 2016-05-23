# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.exceptions
import logging
import os
import time 
import random
import pickle
import re
import subprocess
import traceback
import math
from xml.dom.minidom import parse,parseString
import xmlrpclib
from threading import Thread, Lock
from Queue import Queue, Empty
import json
from simplejson import JSONEncoder
#import cherrypy
import base64
from datetime import datetime
class firmador_firmador(osv.osv_memory):
    _name = 'firmador.firmador'

    def firmar_libro_sii(self, cr, uid, ids, data, context=None):
        cert = data['cert']
        xml =  data['path']
        passwd = data['passwd']
        set_xml = data['name']
        pathbase =  data['pathbase']
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_firma = os.system(pathbase + '/facturador/facturista.sh --firmar_p12 ' + xml+ ' ' +  cert + ' ' + passwd + ' > ' + set_xml)
        return set_xml 

    def enviar_libro_sii(self, cr, uid, ids, data, context=None):
        cert = data['cert']
        xml =  data['path']
        passwd = data['passwd']
        set_xml = data['name']
        pathbase =  data['pathbase']
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_envio = os.system(pathbase + '/facturador/facturista.sh --enviar ' + xml+ ' ' +  set_xml + ' ' +  '"Servidor=maullin.sii.cl;Puerto=443;SSL=1;ArchivoP12=' + cert + ';ContrasenaP12=' + passwd + '"')
        if resp_envio != 0:
            raise openerp.exceptions.Warning('Error al enviar xml.  Contactar administrador') 
        print resp_envio 
        return set_xml 
    
    def firmar_set_prueba_sii(self, cr, uid, ids, data, context=None):
        cert = data['cert']
        xml =  data['path']
        passwd = data['passwd']
        set_xml = '/tmp/SET_%s.xml' % str( datetime.now().strftime('%Y-%m-%d') )
        pathbase =  data['pathbase']
        os.chdir(pathbase + '/facturador/')
        os.system('pwd')
        resp_firma = os.system(pathbase + '/facturador/facturista.sh --firmar_p12 ' + xml+ ' ' +  cert + ' ' + passwd + ' > ' + set_xml)
        return set_xml 
    
    def firmar_dte_prueba_sii(self, cr, uid, ids, data, context=None):
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
            self.guardar_vitacora(cr, uid, mids, modelo, {'state': 'Error', 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Fallo al firmar dte'}, context)
        self.guardar_dte_en_modelo(cr, uid, mids, xmlfirmadosii, modelo, name=name_file)
        self.guardar_vitacora(cr, uid, mids, modelo, {'state': 'Firma DTE SII OK', 'code_sii': str(tipodte), 'folio': str(foliodte),'observacion': 'Proceso de firma DTE'}, context)
        os.remove(rutaxmldte)        
        os.chdir(pathbase+'/facturador/')
        return xmlfirmadosii
    
    def firmar_enviar_sii(self, cr, uid, ids, data, context=None):
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
            self.guardar_vitacora(cr, uid, mids, modelo, {'state': 'Error', 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Fallo al firmar dte'}, context)
        self.guardar_dte_en_modelo(cr, uid, mids, xmlfirmadosii, modelo)
        self.guardar_vitacora(cr, uid, mids, modelo, {'state': 'Firma DTE SII OK', 'code_sii': str(tipodte), 'folio': str(foliodte),'observacion': 'Proceso de firma DTE'}, context)
        respenviosii = pathbase + '/out/resp_sii/respsii' + rutemisor + tipodte + foliodte + '.txt'
        os.remove(rutaxmldte)        
        os.chdir(pathbase+'/facturador/')
        os.system('pwd')
        resp_envio = os.system(pathbase + '/facturador/facturista.sh --enviar ' + xmlfirmadosii + ' ' + respenviosii   + ' ' +  '"Servidor=maullin.sii.cl;Puerto=443;SSL=1;ArchivoP12=' + rutacertpfx + ';ContrasenaP12=' + contcertpxpfx + '"')
        if resp_envio != 0:
            self.guardar_vitacora(cr, uid, mids, modelo, {'state': 'Error', 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Fallo al enviar dte a SII'}, context)
        mirespuestasii = open(respenviosii,'r')
        datosrespuestasii = mirespuestasii.read()
        inicioxmlrespuesta = datosrespuestasii.find('<?xml version="1.0"?>')
        textoxmlrespuestasii =     datosrespuestasii[inicioxmlrespuesta:]
        midomresp=parseString(textoxmlrespuestasii)
        timestamp = midomresp.getElementsByTagName("TIMESTAMP")[0].firstChild.nodeValue
        status = midomresp.getElementsByTagName("STATUS")[0].firstChild.nodeValue
        trackid = midomresp.getElementsByTagName("TRACKID")[0].firstChild.nodeValue
        self.guardar_vitacora(cr, uid, mids, modelo, {'state': str(status), 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Upload DTE correcto'}, context)
        self.pool.get(modelo).write(cr, uid, mids,{'trackid' : trackid})
        return xmlfirmadosii

    def fimar_cliente(self, cr, uid, ids, data, context=None):
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
            self.guardar_vitacora(cr, uid, mids, modelo, {'state': 'Error', 'code_sii': tipodte, 'folio': foliodte,'observacion': 'Fallo al firmar dte'}, context)
        self.guardar_dte_en_modelo(cr, uid, mids, xmlfirmadosii, modelo)
        self.guardar_vitacora(cr, uid, mids, modelo, {'state': 'Firma DTE SII OK', 'code_sii': str(tipodte), 'folio': str(foliodte),'observacion': 'Proceso de firma DTE'}, context)
        midom=parse(xmlfirmadosii)
        elements = midom.getElementsByTagName("TED")
        respuesta = {}
        respuesta['respuesta'] = elements[0].toxml().replace('\n','').replace('\t','')
        respuesta['signed_path'] = xmlfirmadosii
        print respuesta
        os.remove(rutaxmldte)        
        return respuesta
 
    
    def guardar_dte_en_modelo(self, cr, uid, ids, archivo, modelo, name = None):
        print 'guardando'
        b64data = ''
        if name is None:
            name = 'factura.xml'
        try:
            with open(archivo, 'r') as myfile:
                b64data = base64.b64encode(myfile.read())
                myfile.close()
            print b64data
            self.pool.get(modelo).write(cr, uid, ids, {'xml_file': b64data, 'export_filename' : name })
        except:
            print 'fallo al guardar archivo'


    def guardar_vitacora(self, cr, uid, ids, modelo, data, context=None):
        if modelo == 'account.invoice':
            data['invoice'] = ids
        elif modelo == 'stock.picking.out':
            data['picking_out_id'] = ids
        elif modelo == 'stock.picking.in':
            data['picking_out_in'] = ids
        self.pool.get('account.invoice.emitidos').create(cr, uid, data)
        return True