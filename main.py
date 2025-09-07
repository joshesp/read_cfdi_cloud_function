import functions_framework
from flask import jsonify
from lxml import etree

VALID_VERSIONS = {"4.0"}
NAMES_SPACES = {
    "cfdi": "http://www.sat.gob.mx/cfd/4",
    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
}


@functions_framework.http
def read_cfdi(request):
    ## Set CORS headers for the preflight request
    if request.method == "OPTIONS":
        ## Allows GET requests from any origin with the Content-Type
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }

        return ("", 204, headers)

    # Set CORS headers for the main request
    headers = {"Access-Control-Allow-Origin": "*"}

    if "upfile" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["upfile"]

    if "xml" not in file.content_type:
        return jsonify({"error": file.content_type}), 400

    try:
        content = file.read()
        root = etree.fromstring(content)

        missingAttrib = validate_cfdi_structure(root)

        if missingAttrib:
            return jsonify(
                {"error": f"Missing required attributes: {', '.join(missingAttrib)}"}
            ), 400

        if root.attrib["Version"] not in VALID_VERSIONS:
            return jsonify({"error": "Invalid CFDI file"}), 400

        uuid_node = root.xpath("//tfd:TimbreFiscalDigital", namespaces=NAMES_SPACES)

        if not uuid_node:
            return jsonify({"error": "Missing TimbreFiscalDigital"}), 400

        uuid = uuid_node[0].attrib["UUID"]
        emisor = _parse_taxpayer(root.xpath(".//cfdi:Emisor", namespaces=NAMES_SPACES))
        receptor = _parse_taxpayer(
            root.xpath(".//cfdi:Receptor", namespaces=NAMES_SPACES)
        )
        conceptos, impuestos = _parse_concepts_and_taxes(root)

        impuestos_node = root.xpath("./cfdi:Impuestos", namespaces=NAMES_SPACES)
        total_impuesto = 0.0
        if impuestos_node:
            total_impuesto = _safe_float(
                impuestos_node[0].attrib.get("TotalImpuestosTrasladados")
            )

        return (
            {
                "version": root.attrib["Version"],
                "fecha": root.attrib["Fecha"],
                "formaPago": root.attrib.get("FormaPago") or "00",
                "metodoPago": root.attrib.get("MetodoPago"),
                "subTotal": float(root.attrib["SubTotal"]),
                "totalImpuesto": total_impuesto,
                "descuento": float(root.attrib.get("Descuento", 0.0)),
                "moneda": root.attrib["Moneda"],
                "total": float(root.attrib["Total"]),
                "tipoDeComprobante": root.attrib["TipoDeComprobante"],
                "uuid": uuid,
                "emisor": emisor,
                "receptor": receptor,
                "conceptos": conceptos,
                "impuestos": impuestos,
            },
            200,
            headers,
        )
    except etree.XMLSyntaxError:
        return jsonify({"error": "Malformed XML file"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to parse XML: {str(e)}"}), 500


def validate_cfdi_structure(root):
    required_attrs = ["Version", "Fecha", "Moneda", "Total", "TipoDeComprobante"]
    return [attr for attr in required_attrs if attr not in root.attrib]


def _parse_taxpayer(root):
    if root is None:
        return None

    element = root[0]

    return {
        "rfc": element.attrib["Rfc"],
        "nombre": element.attrib["Nombre"],
        "regimenFiscal": element.attrib.get("RegimenFiscal")
        or element.attrib.get("RegimenFiscalReceptor"),
        "usCfdi": element.attrib.get("UsoCFDI"),
    }


def _parse_concepts_and_taxes(root):
    conceptos = []
    impuestos = []

    datConceptos = root.xpath(
        ".//cfdi:Conceptos/cfdi:Concepto",
        namespaces={"cfdi": "http://www.sat.gob.mx/cfd/4"},
    )
    datImpuestos = root.xpath(
        "./cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado",
        namespaces={"cfdi": "http://www.sat.gob.mx/cfd/4"},
    )

    for concepto in datConceptos:
        conceptos.append(
            {
                "claveUnidad": concepto.attrib["ClaveUnidad"],
                "descripcion": concepto.attrib["Descripcion"],
                "importe": _safe_float(concepto.attrib["Importe"]),
                "valorUnitario": _safe_float(concepto.attrib["ValorUnitario"]),
                "descuento": _safe_float(concepto.attrib.get("Descuento")),
                "cantidad": int(_safe_float(concepto.attrib["Cantidad"])),
                "claveProdServ": concepto.attrib["ClaveProdServ"],
                "objetoImp": concepto.attrib["ObjetoImp"],
            }
        )

    for impuesto in datImpuestos:
        impuestos.append(
            {
                "importe": _safe_float(impuesto.attrib["Importe"]),
                "impuesto": impuesto.attrib["Impuesto"],
                "tipoFactor": impuesto.attrib["TipoFactor"],
                "tasaOCuota": _safe_float(impuesto.attrib["TasaOCuota"]),
                "base": _safe_float(impuesto.attrib["Base"]),
            }
        )

    return (
        conceptos,
        impuestos,
    )


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
