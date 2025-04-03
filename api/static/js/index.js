function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

const add_filter = () => {
    const filter_html = `
    <div class="d-flex flex-row border-1 border mb-4 justify-content-center align-items-center bne_and_or" style="width: 120px;height: 30px;" id="bne_and_or_1">
        <span class="text-primary">Y&nbsp&nbsp</span>
            <div class="form-check form-switch">
                <input class="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckDefault" onclick="and_or_switch(this)">
            </div>
            <span class="">O</span>
    </div>
    <div class="container-sm border border-1 d-flex align-items-center my-4  position-relative" style="height:75px">
        <div class="input-group b_filter_group" style="height: 50px;">
            <input  type="text" class="form-control k" placeholder="Nombre, fecha de nacimiento..." onkeydown="show_ul(this)">
            <select class="form-select" aria-label="Default select example">
                <option selected onclick="set_value(this)">con valor</option>
                <option onclick="without_value(this)">sin valor</option>
                <option value="3" onclick="regardless_value(this)">sin importar valor</option>
              </select>
            <input  type="text" class="form-control v" placeholder="Valor" onkeydown="set_filter(this)" id="set_me">
            <div class="d-flex align-items-center">
            <button class="btn" onclick="trash_filter(this)">
                <svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
                    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
                    <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                </svg>
            </button>
            </div>
        </div>
    </div>
`

    const container = document.querySelector("#filter_container");
    const filter_div = document.createElement("div");
    filter_div.innerHTML = filter_html;
    filter_div.className = "filter_div";
    container.appendChild(filter_div);
    return filter_div;
};

let fields = [];

const set_download_link = () => {
    const csv_a = document.querySelector("#d_csv");
    const json_a = document.querySelector("#d_json");
    
    // Construir la URL base para la API
    let baseUrl = new URL(window.location.href);
    const dataset = document.getElementById("dataset").value;
    
    // Crear una nueva URL limpia para la API
    const apiUrl = new URL(`/api/${dataset}`, window.location.origin);
    
    // Agregar parámetros comunes
    apiUrl.searchParams.set("is_from_web", "true");
    
    // Obtener los filtros de la URL actual (excepto preview_mode y view)
    for (const [key, value] of baseUrl.searchParams.entries()) {
        if (key !== "preview_mode" && key !== "view" && key !== "page" && 
            key !== "dataset" && key !== "fields") {
            apiUrl.searchParams.set(key, value);
        }
    }
    
    // Configurar la URL para descargas con los campos actualizados
    if (fields && fields.length > 0) {
        // Verificar que todos los campos sean válidos
        const validFields = fields.filter(field => field && typeof field === 'string');
        
        // Solo agregar fields si hay campos válidos
        if (validFields.length > 0) {
            const fieldParam = validFields.join(",");
            
            // Crear las URLs de descarga
            const csvUrl = new URL(apiUrl);
            csvUrl.pathname += ".csv";
            csvUrl.searchParams.set("fields", fieldParam);
            
            const jsonUrl = new URL(apiUrl);
            jsonUrl.pathname += ".json";
            jsonUrl.searchParams.set("fields", fieldParam);
            
            // Asignar las URLs a los enlaces
            csv_a.href = csvUrl.toString();
            json_a.href = jsonUrl.toString();
            
            // Habilitar el botón de descarga
            const downloadButton = document.getElementById("download_button");
            if (downloadButton) {
                downloadButton.classList.remove("disabled");
            }
            
            return;
        }
    }
    
    // Si no hay campos específicos, descargar todos
    const csvUrl = new URL(apiUrl);
    csvUrl.pathname += ".csv";
    
    const jsonUrl = new URL(apiUrl);
    jsonUrl.pathname += ".json";
    
    csv_a.href = csvUrl.toString();
    json_a.href = jsonUrl.toString();
    
    csv_a.setAttribute("download", `${dataset}.csv`);
    json_a.setAttribute("download", `${dataset}.json`);

    // Habilitar el botón de descarga
    const downloadButton = document.getElementById("download_button");
    if (downloadButton) {
        downloadButton.classList.remove("disabled");
    }
};

const populate_filters = () => {
    const get_args = _ =>
        [...new URLSearchParams(window.location.href.split('?')[1])].reduce(
            (a, [k, v]) => ((a[k] = v), a),
            {}
        );
    let args = get_args();
    
    // Ignorar parámetros que no son filtros
    if ('page' in args) {
        delete args.page;
    }
    
    if ('preview_mode' in args) {
        // Preservar el valor pero no mostrarlo como filtro
        const previewMode = args.preview_mode;
        delete args.preview_mode;
        
        // Actualizar el estado del toggle
        const toggle = document.getElementById('preview-toggle');
        if (toggle) {
            toggle.checked = previewMode === "0";
            updatePreviewMode();
        }
    }
    
    const view_i = Object.keys(args).indexOf("view");
    document.querySelector("#view").value = ["marc", "human"].indexOf(Object.values(args).at(view_i)) >= 0 ? Object.values(args).at(view_i) : "";
    delete args.view;
    
    if (Object.keys(args).length == 0) {
        document.querySelector("#view").value = "human";
        return;
    };
    
    if (!args) {
        return;
    };
    
    // Crear filtros UI para cada parámetro (excepto los ya excluidos)
    let filterIndex = 0;
    Object.entries(args).forEach((arg, i) => {
        const [k, v] = arg;
        if (k !== "dataset" && k !== "is_from_web") {
            if (filterIndex > 0) add_filter();
            filterIndex++;
        }
    });
    
    // Rellenar los valores de filtro
    filterIndex = 0;
    Object.entries(args).forEach((arg) => {
        const [k, v] = arg;
        if (k === "dataset") {
            document.querySelector("#dataset").value = v;
        } else if (k !== "is_from_web") {
            const filter = [...document.querySelectorAll(".filter_div")].at(filterIndex);
            const inputs = Array(...filter.getElementsByTagName("input"));
            inputs[1].value = k;
            inputs[2].value = v;
            filterIndex++;
        }
    });
};

populate_filters();

const set_name_filters = () => {
    for (let filter of document.getElementsByClassName("v")) {
        set_filter(filter);
    };
};

set_name_filters();

const get_headers = () => {
    const view = document.querySelector("#view").value;
    const dataset = document.querySelector("#dataset").value;
    const input_fields = JSON.parse(document.querySelector("#fields").value)[dataset];
    let result = [];
    if (view == "human") {
        for (let field of input_fields) {
            if (!field.startsWith("t_")) {
                result.push(field);
            };
        };
    } else if (view == "marc") {
        for (let field of input_fields) {
            if (field.startsWith("t_")) {
                result.push(field);
            };
        };
    } else {
        result = input_fields;
    };
    return result;
};

const show_data = () => {
    try  {
        document.querySelector("#data").value;
    } catch {
        return;
    };
    const results_div = document.querySelector("#results_div");
    const spinner = document.querySelector("#results_spinner");
    const title = document.querySelector("#results_title");
    const download_button = document.querySelector("#download_button");
    const results_thead = document.querySelector("#results_thead");
    const results_tbody = document.querySelector("#results_tbody");
    results_thead.innerHTML = "";
    results_tbody.innerHTML = "";
    download_button.className = "btn btn-dark dropdown-toggle disabled";
    download_button.innerHTML = "Descargar";
    results_div.className = "container-sm d-flex flex-column justify-content-center mt-5";
    spinner.className = "text-center";
    title.innerHTML = "";
    
    const data = JSON.parse(document.querySelector("#data").value);
    if (!data.success) {
        if (data.message.startsWith("El filtro")) {
            title.innerHTML = data.message;
            spinner.className = "visually-hidden";
            return;
        } 
        else if (data.message == "SQLite3 Operational Error") {
            title.innerHTML = `Debe ser indicado un valor correcto`;
            spinner.className = "visually-hidden";
            return;
        };
        return;
    }
    else if (data.data.length == 0) {
        title.innerHTML = `No hay resultados que cumplan los criterios de búsqueda.`;
        spinner.className = "visually-hidden";
        return;
    };

    spinner.className = "visually-hidden";
    
    // Mostrar información sobre el modo de previsualización si corresponde
    if (data.preview_mode && data.full_record_count) {
        title.innerHTML = `Mostrando previsualización (20 registros de ${formatNumber(data.full_record_count)} encontrados)`;
    } else if (data.total_records !== undefined) {
        title.innerHTML = `${formatNumber(data.total_records)} registros encontrados`;
    }
    
    download_button.className = "btn btn-dark dropdown-toggle";
    const records = data.data;
    const tr_k = document.createElement("tr");
    const new_fields = get_headers();

    for  (let k of new_fields) {
        const th = document.createElement("th");
        const btn_close = document.createElement("button");
        th.style.backgroundColor = "#003164"; 
        btn_close.className = `d-inline btn-close text-white ${k}`;
        btn_close.setAttribute("onclick", "remove_col(this)");
        btn_close.style.alignSelf = "center"; 
        btn_close.style.backgroundColor = "white"; 
        btn_close.style.fontSize = "12px"; 
        btn_close.style.marginLeft = "10px"; 
        try {
            const tooltip_title = tooltips[dataset.value][k];
            th.innerHTML = `<div  class="d-flex justify-content-between text-white"><span class="tooltip_bne"data-bs-custom-class="tooltip_bne" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-title="${tooltip_title}">${k}</span></div>`; // data-bs-toggle="tooltip" data-bs-placement="top" data-bs-title="Tooltip on top"
            th.firstChild.appendChild(btn_close);
            tr_k.appendChild(th)
        } catch {
            const tooltip_title = "Estamos trabajando en ello"
            th.innerHTML = `<div  class="d-flex justify-content-between text-white"><span class="tooltip_bne"data-bs-custom-class="tooltip_bne" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-title="${tooltip_title}">${k}</span></div>`; // data-bs-toggle="tooltip" data-bs-placement="top" data-bs-title="Tooltip on top"
            th.firstChild.appendChild(btn_close);
            tr_k.appendChild(th)
        };
    };
    results_thead.appendChild(tr_k);

    records.forEach((record) => {
        const tr_v = document.createElement("tr");
        for (let k of new_fields) {
            const td = document.createElement("td");
            td.scope = "col";
            td.className = k;
            td.innerHTML = record[k]?record[k].trim():"";
            tr_v.appendChild(td);
        };
        results_tbody.appendChild(tr_v);
    })

    updatePagination(data);
};

if (document.querySelector("#data")) {
    show_data();
};

function updatePagination(data) {
    // Si no hay paginación, ocultar el contenedor
    const paginationContainer = document.getElementById('pagination-container');
    if (!data.total_records || !data.current_page || !data.total_pages) {
        if (paginationContainer) paginationContainer.classList.add('d-none');
        return;
    }
    
    // Mostrar el contenedor de paginación
    paginationContainer.classList.remove('d-none');
    
    // Actualizar información de registros mostrados
    const totalRecords = data.total_records;
    const currentPage = data.current_page;
    const pageSize = data.page_size || 10;
    const totalPages = data.total_pages;
    
    const startRecord = (currentPage - 1) * pageSize + 1;
    const endRecord = Math.min(currentPage * pageSize, totalRecords);
    
    document.getElementById('page-start').textContent = formatNumber(startRecord);
    document.getElementById('page-end').textContent = formatNumber(endRecord);
    document.getElementById('total-records').textContent = formatNumber(totalRecords);
    
    // Actualizar botones de paginación
    const pagination = document.querySelector('.pagination');
    const firstPageItem = document.getElementById('first-page');
    const prevPageItem = document.getElementById('prev-page');
    const nextPageItem = document.getElementById('next-page');
    const lastPageItem = document.getElementById('last-page');
    const pageTemplate = document.getElementById('page-template');
    
    // Habilitar/deshabilitar botones de navegación
    firstPageItem.classList.toggle('disabled', currentPage === 1);
    prevPageItem.classList.toggle('disabled', currentPage === 1);
    nextPageItem.classList.toggle('disabled', currentPage === totalPages);
    lastPageItem.classList.toggle('disabled', currentPage === totalPages);
    
    // Configurar eventos para los botones de navegación
    firstPageItem.querySelector('a').onclick = function(e) {
        e.preventDefault();
        if (currentPage > 1) goToPage(1);
    };
    
    prevPageItem.querySelector('a').onclick = function(e) {
        e.preventDefault();
        if (currentPage > 1) goToPage(currentPage - 1);
    };
    
    nextPageItem.querySelector('a').onclick = function(e) {
        e.preventDefault();
        if (currentPage < totalPages) goToPage(currentPage + 1);
    };
    
    lastPageItem.querySelector('a').onclick = function(e) {
        e.preventDefault();
        if (currentPage < totalPages) goToPage(totalPages);
    };
    
    // Eliminar botones de páginas existentes
    Array.from(pagination.querySelectorAll('.page-item:not(#first-page):not(#prev-page):not(#next-page):not(#last-page):not(#page-template)')).forEach(item => {
        pagination.removeChild(item);
    });
    
    // Determinar qué páginas mostrar
    let pagesToShow = 5; // Ajustar según necesidades
    
    // Reducir pagesToShow si hay muchas páginas y ajustar según espacio disponible
    if (totalPages > 100) pagesToShow = 3;
    
    let startPage = Math.max(1, currentPage - Math.floor(pagesToShow / 2));
    let endPage = Math.min(totalPages, startPage + pagesToShow - 1);
    
    if (endPage - startPage + 1 < pagesToShow && startPage > 1) {
        startPage = Math.max(1, endPage - pagesToShow + 1);
    }
    
    // Crear botones de páginas
    for (let i = startPage; i <= endPage; i++) {
        const pageItem = pageTemplate.cloneNode(true);
        pageItem.id = `page-${i}`;
        pageItem.classList.remove('d-none');
        pageItem.classList.toggle('active', i === currentPage);
        
        const pageLink = pageItem.querySelector('a');
        pageLink.textContent = i;
        pageLink.onclick = function(e) {
            e.preventDefault();
            goToPage(i);
        };
        
        // Insertar antes del botón Siguiente
        pagination.insertBefore(pageItem, nextPageItem);
    }
    
    // Añadir indicadores de más páginas si es necesario
    if (startPage > 1) {
        const ellipsisBefore = pageTemplate.cloneNode(true);
        ellipsisBefore.classList.remove('d-none');
        ellipsisBefore.querySelector('a').textContent = '...';
        ellipsisBefore.querySelector('a').onclick = function(e) {
            e.preventDefault();
        };
        ellipsisBefore.classList.add('disabled');
        pagination.insertBefore(ellipsisBefore, document.getElementById(`page-${startPage}`));
    }
    
    if (endPage < totalPages) {
        const ellipsisAfter = pageTemplate.cloneNode(true);
        ellipsisAfter.classList.remove('d-none');
        ellipsisAfter.querySelector('a').textContent = '...';
        ellipsisAfter.querySelector('a').onclick = function(e) {
            e.preventDefault();
        };
        ellipsisAfter.classList.add('disabled');
        pagination.insertBefore(ellipsisAfter, nextPageItem);
    }
}
// Función para navegar a una página específica
function goToPage(page) {
    const url = new URL(window.location.href);
    url.searchParams.set('page', page);
    window.location.href = url.toString();
}

const remove_col = (button) => {
    // Obtener el nombre de la clase (campo) a eliminar
    const cls_name = button.className.split(" ").at(-1);
    
    // Obtener los headers actuales
    const headers = get_headers();
    
    // Eliminar el campo de los headers
    const headerIndex = headers.indexOf(cls_name);
    if (headerIndex !== -1) {
        headers.splice(headerIndex, 1);
    }
    
    // Actualizar el arreglo fields correctamente
    if (fields.length > 0) {
        const fieldIndex = fields.indexOf(cls_name);
        if (fieldIndex !== -1) {
            fields.splice(fieldIndex, 1);
        }
    } else {
        // Si fields está vacío, inicializarlo con los headers actualizados
        fields = [...headers]; // Creamos una copia para evitar referencias compartidas
    }
    
    console.log("Campos actualizados:", fields); 
    
    // Eliminar el elemento del DOM
    button.parentElement.parentElement.remove();
    
    // Eliminar todas las celdas con esa clase
    const elements = Array.from(document.getElementsByClassName(cls_name));
    elements.forEach((element) => {
        element.remove();
    });
    
    // Actualizar los enlaces de descarga después de eliminar campos
    set_download_link();
};

document.onkeydown= (event) => {
    const key = event.key;
    if (document.activeElement.type == "text") {
        return;
    }
    if (key == "v") {
        document.querySelector("#view").focus();


    } else if (key == "d") {
        document.querySelector("#dataset").focus();
    } else if (key == "r") {
        document.querySelector("#results").focus();
    } else if (key == "f") {
        document.querySelector("#original_filter").focus();
        document.querySelector("#original_filter").value = "";
    } else if (key == "a") {
        document.querySelector("#add_filter").focus();

    };
};
