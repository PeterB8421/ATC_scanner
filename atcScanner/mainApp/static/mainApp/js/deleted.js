/*
Author: Bc. Petr Balok
 */
let currentPage = 1;

function get_del_log(){
    // Get deleted file paths via server API
    const url = new URL('/api/get_deleted_log', window.location.origin);

    url.searchParams.append('page', currentPage.toString());

    const reasonFilter = document.getElementById('reason-filter').value;

    if(reasonFilter !== ""){
        url.searchParams.append('reason', reasonFilter);
    }

    fetch(url)
        .then(response => {
            if(!response.ok){
                return response.json().then(errorData =>{
                    throw errorData;
                })
            }
            return response.json();
        })
        .then(data => {
                // Table content HTML element
                const tableEl = document.getElementById('del-table-content');
                tableEl.innerHTML = "";

                const rows = data.data.map(d => {
                let snrClass = "";
                let durationClass = "";
                let fileClass = "";

                let durationLimitInfo = "";

                const reasonLower = (d.reason || "").toLowerCase();

                // Highlight reason for which the file was deleted
                if (reasonLower.includes("snr")) {
                    snrClass = "table-danger";

                } else if (reasonLower.includes("short")) {
                    durationClass = "table-danger";
                    durationLimitInfo = ` <span class="text-muted small">(Min: ${d.short_limit}s)</span>`;

                } else if (reasonLower.includes("long")) {
                    durationClass = "table-danger";
                    durationLimitInfo = ` <span class="text-muted small">(Max: ${d.long_limit}s)</span>`;

                } else if (reasonLower.includes("empty")) {
                    fileClass = "table-danger";
                }

                const durationValue = d.duration !== null ? d.duration : '<span class="text-muted">N/A</span>';

                return `
                    <tr>
                        <td class="${fileClass}">${d.file_path}</td>
                        <td>${d.reason_text}</td>
                        <td class="${snrClass}">${d.snr !== null ? d.snr : '<span class="text-muted">N/A</span>'}</td>
                        
                        <td class="${durationClass}">${durationValue}${durationLimitInfo}</td>
                        
                        <td>${d.date}</td>
                    </tr>
                `;
            }).join('');
                tableEl.innerHTML = rows;

                // Page navigator
                const pageStats = data.pagination;
                document.getElementById('page-info').textContent = `Page ${pageStats.current_page} of ${pageStats.total_pages}`;
                document.getElementById('prev-page').disabled = !pageStats.has_previous;
                document.getElementById('next-page').disabled = !pageStats.has_next;
                document.getElementById('total-recs').innerHTML = `Total recordings (with current filters): <b>${pageStats.total_recs}</b>`;
        })
}

async function loadReasonFilters() {
    // Get reasons for deletion from database
    try {
        const response = await fetch('/api/get_delete_reasons');
        if (!response.ok) throw new Error("Failed to load filters");

        const data = await response.json();
        const selectElement = document.getElementById('reason-filter');

        // Loop through the JSON and create tags from returned reasons
        data.reasons.forEach(reason => {
            const option = document.createElement('option');
            option.value = reason.value;
            option.textContent = reason.label;
            selectElement.appendChild(option);
        });

    } catch (error) {
        console.error("Error loading reason dropdown:", error);
    }
}

document.addEventListener("DOMContentLoaded", function() {
    // Load reasons for deletion to select element
    loadReasonFilters();
});


document.getElementById('prev-page').addEventListener('click', () => {
    // Go to previous page
    currentPage--;
    get_del_log();
});

document.getElementById('next-page').addEventListener('click', () => {
    // Go to next page
    currentPage++;
    get_del_log();
});

document.getElementById('reason-filter').addEventListener('change', function() {
    // Select element was changed, reload table
    currentPage = 1; // Reset to page 1 after changing the filter value
    get_del_log();
});

// Initialize the table after loading the page
get_del_log();
