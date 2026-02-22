import WaveSurfer from 'https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.esm.js'
import Spectrogram from 'https://unpkg.com/wavesurfer.js@7/dist/plugins/spectrogram.esm.js'

function get_recs(sortKey){
    // Get recordings via server API
    const url = `/api/get_recs?sort=${sortKey}`;

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
            if(data.length === 0){
                // When there are no data, let the user know
                document.getElementById('rec-table').innerText = "There are no recordings yet.";
            }
            else{
                const tableEl = document.getElementById('rec-table-content');
                tableEl.innerHTML = "";

                const rows = data.map(rec => {
                    // Create all rows at once, so the page does not have to re-render for each row
                    return `
                        <tr>
                            <td><a href="${rec.abs_url}">${rec.file_name}</a></td>
                            <td> <audio class="rec-player" controls src="${rec.file_path}"></audio> <div class="spec" style="width: 100%;"></div> </td>
                            <td>${rec.snr}</td>
                            <td>${rec.duration} s</td>
                            <td>${rec.date}</td>
                            <td><a class="btn btn-primary" href="${rec.abs_url}">Detail</a></td>
                        </tr>
                    `;
                }).join('');
                tableEl.innerHTML = rows;

                // Add spectrograms to each row
                const audioEls = tableEl.querySelectorAll("tr");

                audioEls.forEach(row => {
                    const audioEl = row.querySelector(".rec-player");
                    const container = row.querySelector(".spec");

                    const ws = WaveSurfer.create({
                        container: container,
                        media: audioEl,
                        height: 0, // Don't show the default waveform
                        interact: false,
                        plugins: [
                            Spectrogram.create({
                                labels: true,
                                height: 60,
                            }),
                        ],
                    })
                })
            }
        })
        .catch(error => {
            if(error.error){
                console.error(`API error: ${error.error}`);
            }
            else{
                console.error('Error drawing spectrograms!');
            }
        })
}

get_recs('-date');


// Keep track of the current state globally
let currentSortColumn = 'date';
let isDescending = true; // true = minus sign (e.g., -date)

// 1. Grab all headers with the 'sortable-header' class
const sortHeaders = document.querySelectorAll('.sortable-header');

sortHeaders.forEach(header => {
    header.addEventListener('click', () => {
        // Clicked column to sort by
        const clickedColumn = header.getAttribute('data-sort');

        // Flip the arrow direction
        if (currentSortColumn === clickedColumn) {
            // Same column
            isDescending = !isDescending;
        } else {
            // Different column
            currentSortColumn = clickedColumn;
            isDescending = true;
        }

        // Reset all icons to the neutral state
        sortHeaders.forEach(h => {
            const icon = h.querySelector('i');
            icon.className = "bi bi-arrow-down-up text-muted";
        });

        // Highlight the active icon
        const activeIcon = header.querySelector('i');
        activeIcon.className = isDescending ? "bi bi-caret-down-fill" : "bi bi-caret-up-fill";

        // Build the API string
        const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;

        get_recs(apiSortKey);
    });
});