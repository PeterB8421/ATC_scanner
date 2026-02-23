import WaveSurfer from 'https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.esm.js'
import Spectrogram from 'https://unpkg.com/wavesurfer.js@7/dist/plugins/spectrogram.esm.js'

function get_recs(sortKey, filter_date = null){
    // Get recordings via server API
    const url = new URL('/api/get_recs', window.location.origin);

    url.searchParams.append('sort', sortKey);

    if(filter_date){
        url.searchParams.append('filter_date', filter_date);
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
            if(data.length === 0){
                // When there are no data, let the user know
                document.getElementById('rec-table').style.display = "none";
                document.getElementById('empty-message').style.display = "block";
            }
            else{
                document.getElementById('rec-table').style.display = "block";
                document.getElementById('empty-message').style.display = "none";
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
                console.error('Error drawing spectrograms: ', error);
            }
        })
}

get_recs('-date');

/*
Data sorting
 */
// Keep track of the current state globally
let currentSortColumn = 'date';
let isDescending = true;

// Get sortable headers
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


/*
Date filtering
 */
const today = new Date();
let currentYear = today.getFullYear();
let currentMonth = today.getMonth() + 1;

const monthSelect = document.getElementById('month-select');
const yearSelect = document.getElementById('year-select');

// Fill the year select element
const baseYear = today.getFullYear();
for (let y = baseYear; y >= 2000; y--) {
    const option = document.createElement('option');
    option.value = y;
    option.textContent = y;
    yearSelect.appendChild(option);
}

// Listeners for date change from select
monthSelect.addEventListener('change', (e) => {
    currentMonth = parseInt(e.target.value, 10);
    renderCalendar(currentYear, currentMonth);
});

yearSelect.addEventListener('change', (e) => {
    currentYear = parseInt(e.target.value, 10);
    renderCalendar(currentYear, currentMonth);
});

async function renderCalendar(year, month) {
    const grid = document.getElementById('calendar-grid');
    grid.innerHTML = ''; // Clear existing calendar

    document.getElementById('year-select').value = year;
    document.getElementById('month-select').value = month;

    // Fetch the counts from Django
    const paddedMonth = String(month).padStart(2, '0');
    const response = await fetch(`/api/month_counts?year=${year}&month=${paddedMonth}`);
    const countsData = await response.json();

    // Add Day of Week Headers
    const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    daysOfWeek.forEach(day => {
        grid.innerHTML += `<div class="fw-bold text-muted">${day}</div>`;
    });

    let firstDayIndex = new Date(year, month - 1, 1).getDay();
    firstDayIndex = firstDayIndex === 0 ? 6 : firstDayIndex - 1;
    const daysInMonth = new Date(year, month, 0).getDate();

    // Pad the empty days before the 1st of the month
    for (let i = 0; i < firstDayIndex; i++) {
        grid.innerHTML += `<div class="cal-empty"></div>`;
    }

    // Build the actual days
    for (let day = 1; day <= daysInMonth; day++) {
        const paddedDay = String(day).padStart(2, '0');
        const dateString = `${year}-${paddedMonth}-${paddedDay}`;

        // Check if API returned a count for this specific date string
        const count = countsData[dateString] || 0;

        // If there are recordings, show a green badge. Otherwise, show nothing.
        const badgeHtml = count > 0
            ? `<br><span class="badge bg-success">${count}</span>`
            : '<br><span class="badge bg-secondary">0</span>';

        grid.innerHTML += `
            <div class="cal-day" data-date="${dateString}">
                <strong>${day}</strong>
                ${badgeHtml}
            </div>
        `;
    }
}

// Button Listeners to change months
document.getElementById('prev-month').addEventListener('click', () => {
    currentMonth--;
    if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    renderCalendar(currentYear, currentMonth);
});

document.getElementById('next-month').addEventListener('click', () => {
    currentMonth++;
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    renderCalendar(currentYear, currentMonth);
});

// Load the initial calendar on page load
renderCalendar(currentYear, currentMonth);



let activeFilterDate = null;

// Update the Calendar Click Listener
const calendarGrid = document.getElementById('calendar-grid');
const clearButton = document.getElementById('clear-date');

calendarGrid.addEventListener('click', (event) => {
    const clickedDay = event.target.closest('.cal-day');
    if (!clickedDay) return;

    activeFilterDate = clickedDay.getAttribute('data-date');

    // Highlight the clicked day
    document.querySelectorAll('.cal-day').forEach(day => {
        day.classList.remove('bg-primary', 'text-white');
    });
    clickedDay.classList.add('bg-primary', 'text-white');

    // Show the "Clear Selection" button
    clearButton.style.display = 'block';

    const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
    get_recs(apiSortKey, activeFilterDate);
});

// Update the Clear Button Listener
clearButton.addEventListener('click', () => {
    activeFilterDate = null;

    // Remove highlight from all calendar days
    document.querySelectorAll('.cal-day').forEach(day => {
        day.classList.remove('bg-primary', 'text-white');
    });

    // Hide the clear button again
    clearButton.style.display = 'none';

    const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
    get_recs(apiSortKey, null);
});
