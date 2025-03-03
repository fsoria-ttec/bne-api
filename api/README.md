<h1 id="version">
BNE API - Versión: 1.3.1
</h1>

URL BASE: [https://apidatosabiertos.bne.es](https://apidatosabiertos.bne.es)

Para hacer uso del API deberá indicar el conjunto de datos a consultar.

### Registros de autoridad

El formato MARC 21 para datos de autoridad está diseñado para ser un portador de información sobre las formas autorizadas de nombres, materias y subdivisiones de materias que se deben utilizar para construir puntos de acceso en registros MARC. Las formas de estos nombres, materias y subdivisiones de materias que se deben utilizar como referencias a las formas autorizadas y las interrelaciones entre estas formas.

    Geográfico: geo,
    Persona: per,
    Entidades: ent
    Congresos: con
    Genero y Forma: gen
    Materia: mat
    Titulos: tit

### Registros bibliográficos

El formato MARC 21 para datos bibliográficos está diseñado para ser un soporte de información bibliográfica sobre materiales textuales impresos y manuscritos, archivos informáticos, mapas, música, recursos continuos, materiales visuales y materiales mixtos. Los datos bibliográficos suelen incluir títulos, nombres, temas, notas, datos de publicación e información sobre la descripción física de un artículo.
    
    Monografías modernas: mon
    Monografías antiguas: moa
    Manuscritos: mss
    Prensa y Revista: ser
    Partituras: par
    Recursos electrónicos: ele
    Materiales mixtos: mam
    Mapas: map
    Filminas y Transparencias: grp
    Dibujos, Carteles y Fotografias: gra
    Grabaciones sonoras: son
    Videograbaciones: vid
    Kit multimedia: kit


Dataset
-------

Las consultas se hacen mediante la llamade del dataset

    GET api/geo

*   Las respuestas serán emitidas en formato JSON y contarán con las siguientes claves en el caso exitoso:
    
        success: boolean
        time: float
        data: array
    
*   Caso fallido:
    
        success: boolean
        message: str
    
**Ejemplo de respuesta:**

```
{
  "success": true,
  "data": [
    {
      "id": "981061031124808606",
      "t_001": "|a 981061031124808606",
      "t_151": "|a San Vicente del Raspeig|v Mapas",
      "nombre_de_lugar": "San Vicente del Raspeig,  Mapas",
      "obras_relacionadas_en_el_catalogo_BNE": "http://catalogo.bne.es/uhtbin/cgisirsi/0/x/0/05?searchdata1=981061031124808606"
    }
  ],
  "time": 0.000028199981898069
}
```

### Parámetros opcionales:

<h3 id="rowid">
rowid
</h3>

El parametro rowid permite que el usuario determina un rango de líneas en una solicitación. El primer número representa la cantidad de registros y el segundo el índice de partida. Por ejemplo, si queremos los 10 primeros registros del dataset **geo** partindo del índice 15 - o sea, de la linea 15 hasta 25, se utiliza:

    GET api/geo?rowid=10-14

Pues el índice de líneas siempre empieza por el valor 0.

<h3 id="order" class="mt-4">
order by
</h3>

    GET api/geo?order_by=t_781

*   El parámetro **order\_by** permite ordenar los resultados a en base a un determinado campo existente en el modelo.
    
        GET api/geo?order_by=t_781
    
*   Es posible ordenar de manera ascendente y de manera descendente agregando una coma seguido por **asc** o **desc**.
    
        GET api/geo?order_by=t_781,desc
    
<h3 id="fields">
fields
</h3>

    GET api/geo?limit=10&fields=id,t_024

*   El parámetro **fields** permite seleccionar los campos a mostrar por cada registro.
*   Cada campo adicional deberá ser separado por comas.

**Ejemplo de respuesta:**

    GET api/geo?t_024=viaf&fields=id,t_024

```
{
    "success": true,
    "time": 0.01,
    "data": [
        {
            "id":"XX450536",
            "t_024": "|ahttp://id.loc.gov/authorities/names/n79089624|2lcnaf /**/ |ahttp://viaf.org/viaf/316429160|2viaf"
        }
    ]
}
```

Si indicamos un campo inexistente en el conjunto se mostrará el siguiente error:

```
{
    "success": false,
    "message": "This field doesn't exist in the db: 1 - available fields: ('id', 't_001', 't_024'...")
}
```

<h3 id="filters">
Campos filtro
</h3>

Para filtrar una búsqueda por un determinado valor deberemos indicar como parámetro la columna a buscar y el valor por el cual queramos filtrar.

    GET api/geo?t_024=Andalucía

*   Las etiquetas MARC deben ser indicadas con el prefijo **t\_**
*   Cada filtro adicional debe ser agregado como un nuevo parámetro utilizando el caracter **&**

        GET api/geo?t_024=Andalucía&lugar_jerarquico=España

*   La búsqueda será **insensible** a las mayúsculas.
*   El valor introducido será buscado dentro del campo diana/objetivo. Si indicamos **esp** en el campo **lugar\_jerarquico** entregará todos los registros que contengan las letras **esp**

        GET api/geo?lugar_jerarquico=esp

**Ejemplo de respuesta:**

```
{
  "success": true,
  "data": [
    {
      "id": "981061029536408606",
      "lugar_jerarquico": "España,  Cantabria (Comunidad Autónoma),  Miengo,  Mogro"
    },
    {
      "id": "981061028441608606",
      "lugar_jerarquico": "España,  Galicia,  Lugo (Provincia),  Barreiros,  San Miguel de Reinante"
    },
    {
      "id": "981061028441108606",
      "lugar_jerarquico": "España,  Galicia,  Lugo (Provincia),  Castroverde,  Peredo"
    },
    {
      "id": "981061028241408606",
      "lugar_jerarquico": "España,  Madrid (Comunidad Autónoma),  Madrid,  Latina (Madrid, Distrito),  Cuatro Vientos (Madrid, Barrio)"
    },
    {
      "id": "981061028044608606",
      "lugar_jerarquico": "España,  Comunidad Valenciana,  Castellón,  L'Alcora,  Araya"
    }
  ],
  "time": 0.0111535999458283
}
```

Es posible utilizar operadores lógicos, para éste cometido agregar entre valor y valor algunos de los siguientes operadores lógicos:

* AND
* OR
* NOT

**Ejemplo de respuesta:**

    GET api/geo?lugar_jerarquico=españa NOT andorra

```
{
    "success": true,
    "time": 0.0123,
    "data": [
        {
        "id":"XX450557",
        "lugar_jerarquico": "Gran Bretaña, Escocia"
        }
    ]
}
```

Es posible buscar campos sin valor, utilizar **null** o **!null** para buscar campos con valor

**Ejemplo de respuesta:**

    GET api/geo?lugar_jerarquico=null

```
{
    "success": true,
    "time": 0.0123,
    "data": [
        {
        "id":"XX450557",
        "lugar_jerarquico": null
        }
    ]
}
```

Desde la versión 1.1.0 es posible hacer consultas cruzadas, consultar el conjunto de datos **A** con filtros del conjunto de datos **B** La sintaxis es la siguiente: /api/{dataset\_1}?{dataset\_2}={filtro\_1}:{valor},{filtro\_2}:valor

<h3 id="csv">
Descargar
</h3>

Para descargar el conjunto en formato CSV o JSON, agregar al final de la url **.csv** o **.json** respectivamente

    GET api/geo?t_781=Andalucía.csv

<h3 id="joining-queries">
Consultas cruzadas
</h3>

Las consultas cruzadas, están disponibles sobre los conjuntos Monografías Modernas y Persona

    GET api/mon?per=t_100:vito dumas,genero:masculino
```
{
    "success": true,
    "time": 20.33,
    "data": [
        {"id": "bimo0000120763",
        "siglo": "XX"
        }
    ]
}
```

<h3 id="count">
count
</h3>

El parametro **count** permite hacer un contaje del número de registros utilizando **1=TRUE**. El total de registros está asociado a la label **id**.

    GET api/geo?count=1

**Ejemplo de respuesta:**

```
{
  "success": true,
  "data": [
    {
      "id": 138663
    }
  ],
  "time": 0.000058799982070922
}
```

El contaje de registros puede estar asociado a el uso de filtros.

    GET api/geo?nombre_de_lugar=madrid&count=1

**Ejemplo de respuesta:**

```
{
  "success": true,
  "data": [
    {
      "id": 1031
    }
  ],
  "time": 0.00004760012961924
}
```

### Diagramas

Los diagramas de los distintos conjuntos de datos pueden ser consultados [aquí](https://bneapi.infofortis.com/api/schema)

<h3 id="tutorial">
Tutorial
</h3>

Con ánimo de facilitar el uso de ésta aplicación, ofrecememos el siguiente ejemplo consultado el conjunto de datos **Persona**, recomendamos utilizar Firefox o Microsoft Edge, ya que ambos muestran la respuesta en JSON en un formato legible. 

Si queremos utilizar Google Chrome os recomendamos agregar la extensión <a href="https://chrome.google.com/webstore/detail/json-viewer/gbmdgpbipfallnflgajpaliibnhdgobh" target="_blank">JSON Viewer</a> , aunque bajo ningún punto es necesario.

1. Acceder a **https://apidatosabiertos.bne.es/api/per?**

    * Ésta petición nos devolvera los primeros 1000 resultados encontrados en formato JSON:
    * Respuesta:
    <img src="/static/tuto_json.png"
        alt="JSON_1"
        />
    
2. Para filtrar los datos encontrados en el paso anterior, debemos agregar los filtros y su valor, separados por **=**

    * Filtrar por **nombre de persona**, nombre_de_persona=**Fernández**
    * https://apidatosabiertos.bne.es/api/per?**nombre_de_persona=Fernández**
    * Respuesta:
    <img src="/static/tuto_json2.png"
        alt="JSON_2"
        />

3. Para agregar más filtros debemos separar las parejas **filtro=valor** con el caracter **&**

    * https://apidatosabiertos.bne.es/api/per?nombre_de_persona=Fernández**&genero=masculino**
    * Respuesta:
    <img src="/static/tuto_json3.png"
        alt="JSON_2"
        />

4. Si queremos mostrar solo algunos campos como por ejemplo el **id**, **nombre_de_persona** y **género**, podemos agregar la clave **fields** separados por comas y sin espacios entre ellos:
    
    * https://apidatosabiertos.bne.es/api/per?nombre_de_persona=Fernández&genero=masculino**&fields=id,nombre_de_persona,genero**
    * Respuesta: 
    <img src="/static/tuto_json4.png"
        alt="JSON_2"
        />

5. Una vez tengamos el conjunto filtrado con los campos que deseamos ver, agregaremos **.json** o **.csv** al final, para descargar los resultados.
    * https://apidatosabiertos.bne.es/api/per?nombre_de_persona=Fernández&genero=masculino&fields=id,nombre_de_persona,genero**.csv**
    * Respuesta: 
    <img src="/static/tuto_csv.png" class="my-4"
        alt="JSON_2"
        />
    * CSV:
    <img src="/static/tuto_csv2.png"
        alt="JSON_2"
        />

<h3 id="examples">
Ejemplos de consulta
</h3>

Algunos ejemplos de consulta 

###### Guitarristas nacidos en **Andalucía**

```
/api/per?lugar_nacimiento=andalucía&ocupacion=guitarrista
```

###### Libros escritos en inglés durante la Guerra Civil (1936-1939) sobre la temática

```
/api/mon?fecha_de_publicacion=1936-1939&lengua_principal=inglés&tema=guerra civil
```

###### Todos los registros geográficos de País Vasco

```
api/geo?t_781=país vasco
```

###### Archivos sonoros en soporte **discos**

```
api/son?soporte=disco
```

###### Revistas en formatos digital

```
/api/ser?t_655=páginas web
```

###### Sólo los títulos de libros escritos por autores españoles nacidos en el siglo **XIX**
```
/api/mon?per=fecha_nacimiento:1900-1999,lugar_nacimiento:españa&fields=titulo
```

###### Libros anterios a 1831 escritos en inglés pero **NO** en español

```
/api/moa?lengua_principal=inglés NOT español
```

###### Sólo titulos, lengua principal y fecha de publicación de libros en francés o aleman publicados durante la decada del 60 del siglo **XIX**

```
/api/mon?lengua_principal=francés OR alemán&decada=60&siglo=xix&fields=lengua_principal,titulo,fecha_de_publicacion
```

###### Entidades con identificador ISNI

```
/api/ent?t_024=isni
```

###### Solo campos bibliotecarios de revistas publicadas en España de la decada del 30 del siglo **XX** ordenados por **editorial**

```
/api/ser?lugar_de_publicacion=españa&view=marc&decada=30&siglo=xx&order_by=editorial
```
