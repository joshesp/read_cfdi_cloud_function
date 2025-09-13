# Lector de CFDI a JSON - Cloud Function

Esta Google Cloud Function procesa facturas electrónicas de México (CFDI) en formato XML y extrae la información relevante, devolviéndola en un formato JSON estructurado.

## Características

- Extrae los datos principales de un CFDI 4.0.
- Extrae la información del Emisor y Receptor.
- Extrae todos los conceptos de la factura.
- Extrae los impuestos trasladados.
- Valida la estructura básica del CFDI.
- Manejo de errores para archivos malformados o inválidos.
- Habilitado para CORS para ser llamado desde aplicaciones web.

## Despliegue

Para desplegar esta función, puedes usar la CLI de `gcloud`:

```bash
gcloud functions deploy read_cfdi \
  --gen2 \
  --runtime python311 \
  --region us-central1 \
  --source . \
  --entry-point read_cfdi \
  --trigger-http \
  --allow-unauthenticated
```

## Uso

Una vez desplegada, la función se puede invocar a través de una petición HTTP POST, enviando el archivo XML del CFDI como `multipart/form-data`.

**Endpoint:** La URL proporcionada por Google Cloud al desplegar la función.

**Método:** `POST`

**Body:** `multipart/form-data` con un campo `upfile` que contiene el archivo XML.

### Ejemplo de uso con cURL

```bash
curl -X POST -F "upfile=@/ruta/a/tu/factura.xml" <URL_DE_LA_FUNCION>
```

## Respuesta Exitosa (200)

Si el CFDI es procesado correctamente, la función devolverá un objeto JSON con la siguiente estructura:

```json
{
  "version": "4.0",
  "fecha": "2023-01-01T12:00:00",
  "formaPago": "01",
  "metodoPago": "PUE",
  "subTotal": 100.00,
  "totalImpuesto": 16.00,
  "descuento": 0.0,
  "moneda": "MXN",
  "total": 116.00,
  "tipoDeComprobante": "I",
  "uuid": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
  "emisor": {
    "rfc": "RFCEMISOR",
    "nombre": "NOMBRE EMISOR",
    "regimenFiscal": "601"
  },
  "receptor": {
    "rfc": "RFCRECEPTOR",
    "nombre": "NOMBRE RECEPTOR",
    "regimenFiscal": "616",
    "usCfdi": "G03"
  },
  "conceptos": [
    {
      "claveUnidad": "E48",
      "descripcion": "Servicio",
      "importe": 100.00,
      "valorUnitario": 100.00,
      "descuento": 0.0,
      "cantidad": 1,
      "claveProdServ": "84111506",
      "objetoImp": "02"
    }
  ],
  "impuestos": [
      {
          "base": 100.00,
          "importe": 16.00,
          "impuesto": "002",
          "tasaOCuota": 0.160000,
          "tipoFactor": "Tasa"
      }
  ]
}
```

## Errores

La función puede devolver los siguientes errores:

- **400 Bad Request:**
  - `{"error": "No file provided"}`: Si no se envía ningún archivo.
  - `{"error": "Invalid CFDI file"}`: Si el archivo no es un CFDI 4.0.
  - `{"error": "Missing TimbreFiscalDigital"}`: Si el CFDI no está timbrado.
  - `{"error": "Malformed XML file"}`: Si el archivo XML está malformado.
  - `{"error": "Missing required attributes: <attributes>"}`: Si faltan atributos requeridos en el nodo principal del CFDI.
- **500 Internal Server Error:**
  - `{"error": "Failed to parse XML: <details>"}`: Si ocurre un error inesperado durante el procesamiento.

## Dependencias

- `functions-framework`: Framework para escribir Cloud Functions en Python.
- `lxml`: Librería para procesar XML.