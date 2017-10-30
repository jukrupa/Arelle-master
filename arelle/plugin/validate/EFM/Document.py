'''
Created on Dec 12, 2013

@author: Mark V Systems Limited
(c) Copyright 2013 Mark V Systems Limited, All rights reserved.
'''
import re
from arelle import ModelDocument, UrlUtil, XbrlConst, XmlUtil
from arelle.ModelObject import ModelObject
from arelle.ValidateXbrlDTS import arcFromConceptQname, arcToConceptQname

inlineDisplayNonePattern = re.compile(r"display\s*:\s*none")

def checkDTSdocument(val, modelDocument, isFilingDocument):
    for hrefElt, _hrefedDoc, hrefId in modelDocument.hrefObjects:
        if hrefId:  #check scheme regardless of whether document loaded 
            # check all xpointer schemes
            for scheme, _path in XmlUtil.xpointerSchemes(hrefId):
                if scheme == "element" and val.validateDisclosureSystem:
                    val.modelXbrl.error(("EFM.6.03.06", "GFM.1.01.03"),
                        _("Href $(elementHref) may only have shorthand xpointers"),
                        modelObject=hrefElt, 
                        elementHref=hrefElt.get("{http://www.w3.org/1999/xlink}href"))
    
    if not isFilingDocument:
        return  # not a filing's extension document
    
    if modelDocument.type == ModelDocument.Type.SCHEMA:
        if modelDocument.targetNamespace is not None and len(modelDocument.targetNamespace) > 85:
            l = len(modelDocument.targetNamespace.encode("utf-8"))
            if l > 255:
                val.modelXbrl.error("EFM.6.07.30",
                    _("[du-0730-uri-length-limit]  Shorten this declaration URI to 255 bytes or fewer in UTF-8: $(value)."),
                    modelObject=modelDocument.xmlRootElement, length=l, targetNamespace=modelDocument.targetNamespace, value=modelDocument.targetNamespace)

    if modelDocument.type in (ModelDocument.Type.SCHEMA, ModelDocument.Type.LINKBASE):
        isSchema = modelDocument.type == ModelDocument.Type.SCHEMA
        if isSchema:
            for elt in modelDocument.xmlRootElement.iter(tag="{http://www.w3.org/2001/XMLSchema}*"):
                if elt.namespaceURI == XbrlConst.xsd:
                    localName = elt.localName
                    if localName in {"element", "complexType", "simpleType"}:
                        name = elt.get("name")
                        if name and len(name) > 64:
                            l = len(name.encode("utf-8"))
                            if l > 200:
                                val.modelXbrl.error("EFM.6.07.29",
                                    _("[du-0729-name-length-limit] Shorten this declaration name to 200 bytes or fewer in UTF-8: $(name)"),
                                    modelObject=elt, element=localName, name=name, length=l)
    
    for elt in modelDocument.xmlRootElement.iter():
        if isinstance(elt, ModelObject):
            xlinkType = elt.get("{http://www.w3.org/1999/xlink}type")
            xlinkRole = elt.get("{http://www.w3.org/1999/xlink}role")
            if elt.namespaceURI == XbrlConst.link:
                # check schema roleTypes        
                if elt.localName in ("roleType","arcroleType"):
                    uriAttr = {"roleType":"roleURI", "arcroleType":"arcroleURI"}[elt.localName]
                    roleURI = elt.get(uriAttr)
                    if len(roleURI) > 85:
                        l = len(roleURI.encode("utf-8"))
                        if l > 255:
                            val.modelXbrl.error("EFM.6.07.30",
                                _("[du-0730-uri-length-limit]  Shorten this declaration URI to 255 bytes or fewer in UTF-8: $(value)."),
                                modelObject=elt, element=elt.qname, attribute=uriAttr, length=l, roleURI=roleURI, value=roleURI)
    
                if elt.localName == "arcroleRef":
                    refUri = elt.get("arcroleURI")
                    hrefAttr = elt.get("{http://www.w3.org/1999/xlink}href")
                    hrefUri, hrefId = UrlUtil.splitDecodeFragment(hrefAttr)
                    if hrefUri not in val.disclosureSystem.standardTaxonomiesDict:
                        val.modelXbrl.error(("EFM.6.09.06", "GFM.1.04.06"),
                            _("[fs-0906-Custom-Arcrole-Referenced] An arcroleRef element refers to $(xlinkHref), an arcrole, $(refURI), that is not defined in a standard taxonomy, in $(refSource). Please recheck submission."),
                            modelObject=elt, refURI=refUri, xlinkHref=hrefUri)
            if modelDocument.type == ModelDocument.Type.INLINEXBRL and elt.namespaceURI in XbrlConst.ixbrlAll: 
                if elt.localName == "footnote":
                    if val.validateGFM:
                        if elt.get("{http://www.w3.org/1999/xlink}arcrole") != XbrlConst.factFootnote:
                            # must be in a nonDisplay div
                            if not any(inlineDisplayNonePattern.search(e.get("style") or "")
                                       for e in XmlUtil.ancestors(elt, XbrlConst.xhtml, "div")):
                                val.modelXbrl.error(("EFM.N/A", "GFM:1.10.16"),
                                    _("Inline XBRL footnote %(footnoteID)s must be in non-displayable div due to arcrole %(arcrole)s"),
                                    modelObject=elt, footnoteID=elt.get("footnoteID"), 
                                    arcrole=elt.get("{http://www.w3.org/1999/xlink}arcrole"))
                            
                        if not elt.get("{http://www.w3.org/XML/1998/namespace}lang"):
                            val.modelXbrl.error(("EFM.N/A", "GFM:1.10.13"),
                                _("Inline XBRL footnote %(footnoteID)s is missing an xml:lang attribute"),
                                modelObject=elt, footnoteID=id)
            if xlinkType == "extended":
                if not xlinkRole or xlinkRole == "":
                    val.modelXbrl.error(("EFM.6.09.04", "GFM.1.04.04"),
                        "[fs-0904-Resource-Role-Missing]  The $(element) element requires an xlink:role such as the default, 'http://www.xbrl.org/2003/role/label', in $(refSource).  Please recheck submission.",
                        modelObject=elt, element=elt.qname)
                if not val.extendedElementName:
                    val.extendedElementName = elt.qname
                elif val.extendedElementName != elt.qname:
                    val.modelXbrl.error(("EFM.6.09.07", "GFM:1.04.07"),
                        _("[cp-0907-Linkbases-Distinct] Your filing contained extended type links with roles of different namesapces and local names, $(element) and $(element2) in the same linkbase, $(refUrl).  Please recheck your submission and ensure that all extended-type links in a single linkbase have the same namespace and local name."),
                        modelObject=elt, element=elt.qname, element2=val.extendedElementName)
            elif xlinkType == "resource":
                if not xlinkRole:
                    val.modelXbrl.error(("EFM.6.09.04", "GFM.1.04.04"),
                        _("[fs-0904-Resource-Role-Missing]  The $(element) element requires an xlink:role such as the default, 'http://www.xbrl.org/2003/role/label', in $(refSource).  Please recheck submission."),
                        modelObject=elt, element=elt.qname)
                elif not XbrlConst.isStandardRole(xlinkRole):
                    modelsRole = val.modelXbrl.roleTypes.get(xlinkRole)
                    if (modelsRole is None or len(modelsRole) == 0 or 
                        modelsRole[0].modelDocument.targetNamespace not in val.disclosureSystem.standardTaxonomiesDict):
                        val.modelXbrl.error(("EFM.6.09.05", "GFM.1.04.05"),
                            _("[fs-0905-Custom-Resource-Role-Used]  The $(element) element has a role, $(roleDefinition), that is not defined in a standard taxonomy, resource labeled $(xlinkLabel), in $(refSource).  Please recheck submission."),
                            modelObject=elt, xlinkLabel=elt.get("{http://www.w3.org/1999/xlink}label"), role=xlinkRole, element=elt.qname,
                            roleDefinition=val.modelXbrl.roleTypeDefinition(xlinkRole))
            elif xlinkType == "arc":
                if elt.get("priority") is not None:
                    priority = elt.get("priority")
                    try:
                        if int(priority) >= 10:
                            val.modelXbrl.error(("EFM.6.09.09", "GFM.1.04.08"),
                                _("[du-0909-Relationship-Priority-Not-Less-Than-Ten]  The priority attribute $(priority) has a value of ten or greater, on arc $(arcElement), in $(refSource). Please change the priority to value less than 10 and resubmit."),
                                modelObject=elt, 
                                arcElement=elt.qname,
                                xlinkFrom=elt.get("{http://www.w3.org/1999/xlink}from"),
                                xlinkTo=elt.get("{http://www.w3.org/1999/xlink}to"),
                                priority=priority)
                    except (ValueError) :
                        val.modelXbrl.error(("EFM.6.09.09", "GFM.1.04.08"),
                            _("[du-0909-Relationship-Priority-Not-Less-Than-Ten]  The priority attribute $(priority) has a value of ten or greater, on arc $(arcElement), in $(refSource). Please change the priority to value less than 10 and resubmit."),
                            modelObject=elt, 
                            arcElement=elt.qname,
                            xlinkFrom=elt.get("{http://www.w3.org/1999/xlink}from"),
                            xlinkTo=elt.get("{http://www.w3.org/1999/xlink}to"),
                            priority=priority)
                if elt.namespaceURI == XbrlConst.link:
                    if elt.localName == "presentationArc" and not elt.get("order"):
                        val.modelXbrl.error(("EFM.6.12.01", "GFM.1.06.01"),
                            _("[rq-1201-Presentation-Order-Missing] The presentation relationship from $(conceptFrom) to $(conceptTo) does not have an order attribute, in $(refSource).  Please provide a value."),
                            modelObject=elt, 
                            xlinkFrom=elt.get("{http://www.w3.org/1999/xlink}from"),
                            xlinkTo=elt.get("{http://www.w3.org/1999/xlink}to"),
                            conceptFrom=arcFromConceptQname(elt),
                            conceptTo=arcToConceptQname(elt))
                    elif elt.localName == "calculationArc":
                        if not elt.get("order"):
                            val.modelXbrl.error(("EFM.6.14.01", "GFM.1.07.01"),
                                _("[du-1401-Calculation-Relationship-Order-Missing] The calculation relationship from $(conceptFrom) to $(conceptTo) does not have an order attribute, in $(refSource)."),
                                modelObject=elt, 
                                xlinkFrom=elt.get("{http://www.w3.org/1999/xlink}from"),
                                xlinkTo=elt.get("{http://www.w3.org/1999/xlink}to"),
                                conceptFrom=arcFromConceptQname(elt),
                                conceptTo=arcToConceptQname(elt))
                        try:
                            weightAttr = elt.get("weight")
                            weight = float(weightAttr)
                            if not weight in (1, -1):
                                val.modelXbrl.error(("EFM.6.14.02", "GFM.1.07.02"),
                                    _("[fs-1402-Calculation-Relationship-Weight-Not-Unitary] Weight value $(weight) on the calculation relationship from $(conceptFrom) to $(conceptTo) must be equal to 1 or to -1, in $(refSource). Please recheck submission."),
                                    modelObject=elt, 
                                    xlinkFrom=elt.get("{http://www.w3.org/1999/xlink}from"),
                                    xlinkTo=elt.get("{http://www.w3.org/1999/xlink}to"),
                                    conceptFrom=arcFromConceptQname(elt),
                                    conceptTo=arcToConceptQname(elt),
                                    weight=weightAttr)
                        except ValueError:
                            val.modelXbrl.error(("EFM.6.14.02", "GFM.1.07.02"),
                                _("[fs-1402-Calculation-Relationship-Weight-Not-Unitary] Weight value $(weight) on the calculation relationship from $(conceptFrom) to $(conceptTo) must be equal to 1 or to -1, in $(refSource). Please recheck submission."),
                                modelObject=elt, 
                                xlinkFrom=elt.get("{http://www.w3.org/1999/xlink}from"),
                                xlinkTo=elt.get("{http://www.w3.org/1999/xlink}to"),
                                conceptFrom=arcFromConceptQname(elt),
                                conceptTo=arcToConceptQname(elt),
                                weight=weightAttr)
                    elif elt.localName == "definitionArc":
                        if not elt.get("order"):
                            val.modelXbrl.error(("EFM.6.16.01", "GFM.1.08.01"),
                                _("[du-1601-Definition-Relationship-Order-Missing] The Definition relationship from $(conceptFrom) to $(conceptTo) does not have an order attribute, in $(refSource)."),
                                modelObject=elt, 
                                xlinkFrom=elt.get("{http://www.w3.org/1999/xlink}from"),
                                xlinkTo=elt.get("{http://www.w3.org/1999/xlink}to"),
                                conceptFrom=arcFromConceptQname(elt),
                                conceptTo=arcToConceptQname(elt))
