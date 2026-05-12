/*
Author: Bc. Petr Balok
 */
import WaveSurfer from 'https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.esm.js'
import Spectrogram from 'https://unpkg.com/wavesurfer.js@7/dist/plugins/spectrogram.esm.js'

/*
============================
Global variables
============================
 */
// Keep track of the current state globally
let currentSortColumn = 'date'; // Column selected for sorting
let isDescending = true;

// Get sortable headers
const sortHeaders = document.querySelectorAll('.sortable-header');
// Day filter
let activeFilterDate = null;
// Hour filter
let activeFilterHour = null;

// Calendar grid and clear button
const calendarGrid = document.getElementById('calendar-grid');
const clearButton = document.getElementById('clear-date');
// Page counter
let currentPage = 1;
let totalPages = 1;

// Graphs for average SNR (month and day)
let monthlyChart = null;
let dailyChart = null;

// Fallback mode flag, if true, there are problems with database and data is read directly from system disk
let isFallback = false;
// Filter by frequency
let selectedFreq = "";
// Filter by airport code
let selectedCode = "";

/*
============================
Get recordings from backend
============================
 */
function get_recs(sortKey){
    /*
     Get recordings via server API

     sortKey - REQUIRED, name of column that should be used for sorting
     */
    const url = new URL('/api/get_recs', window.location.origin);
    let filter_date = activeFilterDate; // Filter by selected date (null if not selected)
    let filter_hour = activeFilterHour; // Filter by selected hour (null if not selected)

    url.searchParams.append('sort', sortKey);
    url.searchParams.append('page', currentPage.toString());

    if(filter_date){
        url.searchParams.append('filter_date', filter_date);
    }
    if(filter_hour){
        url.searchParams.append('filter_hour', filter_hour);
    }
    if(selectedFreq !== ""){
        url.searchParams.append('freq', selectedFreq);
    }
    if(selectedCode !== ""){
        url.searchParams.append('code', selectedCode);
    }

    fetch(url)
        .then(response => {
            if(!response.ok){
                return response.json().then(errorData =>{
                    throw errorData;
                })
            }

            // Check if server returned error with database
            isFallback = response.headers.get('X-Fallback-Mode') === 'true';
            console.log("Fallback mode: ", isFallback);
            if(isFallback){
                // Show fallback mode warnings
                document.getElementById('dailyChart').style.display = "none";
                document.getElementById('empty-message-day').style.display = "none";
                document.getElementById('not-selected-message').style.display = "none";
                document.getElementById('fallback-message-month').style.display = "block";
                document.getElementById('fallback-message-day').style.display = "block";
            }

            const warnBanner = document.getElementById("fallback-warning");

            if(warnBanner){
                // Another fallback mode warning
                warnBanner.style.display = isFallback ? 'flex' : 'none';
            }
            return response.json();
        })
        .then(data => {
            if(data.data.length === 0){
                // When there are no data, let the user know
                const tableEl = document.getElementById('rec-table-content');
                tableEl.innerHTML = "";
                const emptyRow = document.createElement('td');
                emptyRow.setAttribute('colspan', '8');
                emptyRow.innerHTML = "No recordings were found.";
                tableEl.appendChild(emptyRow);

                document.querySelectorAll('.jump-to-page-input').forEach(el => el.value = 1);
                document.querySelectorAll('.total-pages-info').forEach(el => el.textContent = `of 1`);
                document.querySelectorAll('.prev-page-btn').forEach(el => el.disabled = true);
                document.querySelectorAll('.next-page-btn').forEach(el => el.disabled = true);
                document.getElementById('total-recs').innerHTML = `Total recordings (with current filters): <b>0</b>`;
            }
            else{
                // If there are data, populate the table
                if(isFallback){
                    // In fallback mode, only data for newest day was returned
                    activeFilterDate = data.data[0].date.split("T")[0]; // Parse date string from first item
                    currentYear = activeFilterDate.split("-")[0]; // Set current year
                    currentMonth = activeFilterDate.split("-")[1]; // Set current month
                    renderCalendar(currentYear, currentMonth, activeFilterDate); // Highlight returned day
                }
                document.getElementById('rec-table').style.display = "block"; // Show recordings table
                document.getElementById('empty-message').style.display = "none"; // Hide empty message
                const tableEl = document.getElementById('rec-table-content');
                tableEl.innerHTML = "";

                const rows = data.data.map(rec => {
                    /*
                    Iterate over returned data and create table rows
                     */
                    let transcriptClass = ""; // Add color background to transcript cell
                    if(rec.transcript === "[Processing...]"){
                        transcriptClass = "table-info"; // Light blue if transcript is processing
                    }
                    else if(rec.transcript === "[Transcription failed]"){
                        transcriptClass = "table-danger"; // Red if transcript failed
                    }
                    // Create all rows at once, so the page does not have to re-render for each row
                    return `
                        <tr>
                            <td><a href="${rec.abs_url}"><i class="bi bi-soundwave"></i>${rec.file_name}</a></td>
                            <td> <audio class="rec-player" controls src="${rec.file_path}"></audio> <div class="spec" style="width: 100%;"></div> </td>
                            <td>${rec.snr} dB</td>
                            <td>${rec.duration} s</td>
                            <td>${rec.date}</td>
                            <td>${rec.freq} MHz</td>
                            <td>${rec.code}</td>
                            <td class="${transcriptClass}"><div class="text-truncate" style="max-width: 250px; cursor: help" title="${rec.transcript}">${rec.transcript}</div></td>
                            <td><a class="btn btn-primary" href="${rec.abs_url}">Detail</a><button class="btn btn-danger deleteBtn" data-filepath="${rec.file_path}">Delete</button></td>
                        </tr>
                    `;
                }).join('');
                tableEl.innerHTML = rows; // Set rows HTML elements to table body

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
                // Page navigator
                const pageStats = data.pagination;
                totalPages = pageStats.total_pages;

                document.querySelectorAll('.jump-to-page-input').forEach(el => el.value = pageStats.current_page); // Page number input field
                document.querySelectorAll('.total-pages-info').forEach(el => el.textContent = `of ${pageStats.total_pages}`); // Total pages text
                document.querySelectorAll('.prev-page-btn').forEach(el => el.disabled = !pageStats.has_previous); // Previous page button (disable if last page)
                document.querySelectorAll('.next-page-btn').forEach(el => el.disabled = !pageStats.has_next); // Next page button (disable if first page)
                document.getElementById('total-recs').innerHTML = `Total recordings (with current filters): <b>${pageStats.total_recs}</b>`; // Count of all recordings text
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

async function loadMonthlyChart(year, month) {
    /*
    Load chart for average SNR for selected month and year

    year - REQUIRED
    month - REQUIRED
     */
    if(isFallback){
        // Show warning in fallback mode
        document.getElementById('monthlyChart').style.display = "none";
        document.getElementById('empty-message-month').style.display = "none";
        document.getElementById('not-selected-message').style.display = "none";
        document.getElementById('fallback-message-month').style.display = "block";
        return;
    }
    document.getElementById('fallback-message-month').style.display = "none";
    const response = await fetch(`/api/get_monthly_snr?year=${year}&month=${month}`); // Get average SNR data for days in selected month and year
    const data = await response.json();

    isFallback = response.headers.get('X-Fallback-Mode') === 'true';
    console.log("Fallback mode: ", isFallback);
    if(isFallback){
        // Show warning when in fallback mode
        document.getElementById('monthlyChart').style.display = "none";
        document.getElementById('empty-message-month').style.display = "none";
        document.getElementById('not-selected-message').style.display = "none";
        document.getElementById('fallback-message-month').style.display = "block";
        document.getElementById('fallback-message-day').style.display = "block";
        return;
    }

    const ctx = document.getElementById('monthlyChart').getContext('2d');
    const emptyMsg = document.getElementById('empty-message-month');
    const selectedMonth = document.getElementById('month-select').selectedOptions[0].text; // Get month value from select element
    const selectedYear = document.getElementById('year-select').selectedOptions[0].text; // Get year value from select element
    document.getElementById('selectedMonthText').innerHTML = `${selectedMonth} ${selectedYear}`; // Set header text for the chart

    // Destroy previous chart instance if it exists
    if (monthlyChart) monthlyChart.destroy();

    if(data.labels.length === 0){
        // If there is no data for selected month, show empty message
        document.getElementById('monthlyChart').style.display = "none";
        emptyMsg.style.display = "block";
    }
    else{
        // Otherwise show the chart
        document.getElementById('monthlyChart').style.display = "block";
        emptyMsg.style.display = "none";
    }

    // Average SNR per day chart
    monthlyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Avg SNR (dB)',
                data: data.data,
                backgroundColor: 'rgba(13, 110, 253, 0.7)', // Bootstrap Primary
                borderColor: '#0d6efd',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true } }
        }
    });
}

async function loadDailyChart(date) {
    /*
    Load average hourly SNR chart for selected day

    date - REQUIRED, selected date string
     */
    if(isFallback){
        // Show warning in fallback mode
        document.getElementById('dailyChart').style.display = "none";
        document.getElementById('empty-message-day').style.display = "none";
        document.getElementById('not-selected-message').style.display = "none";
        document.getElementById('fallback-message-day').style.display = "block";
        return;
    }
    document.getElementById('fallback-message-day').style.display = "none";
    if(!date){
        // Show message when date was not selected (date === null)
        document.getElementById('dailyChart').style.display = "none";
        document.getElementById('empty-message-day').style.display = "none";
        document.getElementById('not-selected-message').style.display = "block";
        return;
    }
    document.getElementById('not-selected-message').style.display = "none";
    document.getElementById('selectedDayText').innerHTML = date; // Set chart header
    const response = await fetch(`/api/get_daily_snr?date=${date}`); // Get data from server
    const data = await response.json();

    isFallback = response.headers.get('X-Fallback-Mode') === 'true';
    console.log("Fallback mode: ", isFallback);
    if(isFallback){
        // Show warning in fallback mode
        document.getElementById('dailyChart').style.display = "none";
        document.getElementById('empty-message-day').style.display = "none";
        document.getElementById('not-selected-message').style.display = "none";
        document.getElementById('fallback-message-month').style.display = "block";
        document.getElementById('fallback-message-day').style.display = "block";
        return;
    }

    const ctx = document.getElementById('dailyChart').getContext('2d');
    const emptyMsg = document.getElementById('empty-message-day');

    // Destroy previous chart instance if it exists
    if (dailyChart) dailyChart.destroy();

    if(data.labels.length === 0){
        // If there is no data for selected date, show empty message
        document.getElementById('dailyChart').style.display = "none";
        emptyMsg.style.display = "block";
    }
    else{
        // Otherwise show chart
        document.getElementById('dailyChart').style.display = "block";
        emptyMsg.style.display = "none";
    }

    // Hourly average SNR chart
    dailyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Avg SNR (dB)',
                data: data.data,
                borderColor: '#198754', // Bootstrap Success Green
                backgroundColor: 'rgba(25, 135, 84, 0.2)',
                borderWidth: 2,
                fill: true,
                tension: 0.3 // Smooth curves
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true } }
        }
    });
}

/*
============================
Data sorting
============================
 */

sortHeaders.forEach(header => {
    /*
    Add click listeners for sortable table headers
     */
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

        // Build the sort parameter string
        const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;

        currentPage = 1; // Reset page counter
        get_recs(apiSortKey); // Reload the table
    });
});


/*
============================
Date filtering
============================
 */
const today = new Date();
let currentYear = today.getFullYear();
let currentMonth = today.getMonth() + 1;

const monthSelect = document.getElementById('month-select');
const yearSelect = document.getElementById('year-select');

// Fill the year select element
const baseYear = today.getFullYear();
for (let y = baseYear; y >= 2000; y--) {
    // Add options for years from 2000 to current year
    const option = document.createElement('option');
    option.value = y;
    option.textContent = y;
    yearSelect.appendChild(option);
}

monthSelect.addEventListener('change', (e) => {
    /*
    Month select was changed, re-render the calendar
     */
    currentMonth = parseInt(e.target.value, 10);
    renderCalendar(currentYear, currentMonth);
});

yearSelect.addEventListener('change', (e) => {
    /*
    Year select was changed, re-render the calendar
     */
    currentYear = parseInt(e.target.value, 10);
    renderCalendar(currentYear, currentMonth);
});

async function renderCalendar(year, month, selectedDay = null) {
    /*
    Render the calendar grid

    year - REQUIRED
    month - REQUIRED
    selectedDay - OPTIONAL, highlights the day in this string, format YYYY-MM-DD
     */
    const grid = document.getElementById('calendar-grid'); // Calendar grid div
    grid.innerHTML = ''; // Clear existing calendar

    document.getElementById('year-select').value = year; // Year value from year select
    document.getElementById('month-select').value = month; // Month value from month select

    // Fetch the counts from Django
    const paddedMonth = String(month).padStart(2, '0'); // Add leading zeroes to month
    const response = await fetch(`/api/month_counts?year=${year}&month=${paddedMonth}`); // Get number of recordings for each day in month
    const countsData = await response.json();

    // Add Day of Week Headers
    const daysOfWeek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    daysOfWeek.forEach(day => {
        // Add days of month
        grid.innerHTML += `<div class="fw-bold text-muted">${day}</div>`;
    });

    let firstDayIndex = new Date(year, month - 1, 1).getDay();
    firstDayIndex = firstDayIndex === 0 ? 6 : firstDayIndex - 1; // First weekday is Monday
    const daysInMonth = new Date(year, month, 0).getDate();

    // Pad the empty days before the 1st of the month
    for (let i = 0; i < firstDayIndex; i++) {
        grid.innerHTML += `<div class="cal-empty"></div>`;
    }

    // Build the actual days
    for (let day = 1; day <= daysInMonth; day++) {
        const paddedDay = String(day).padStart(2, '0');
        const dateString = `${year}-${paddedMonth}-${paddedDay}`;

        // Check if API returned a count for this specific day
        const count = countsData[dateString] || 0;

        // If there are recordings, show a green badge. Otherwise, show nothing.
        const badgeHtml = count > 0
            ? `<br><span class="badge bg-success">${count}</span>`
            : '<br><span class="badge bg-secondary">0</span>';

        const highlightClass = (dateString === selectedDay) ? "bg-primary text-white" : "";

        grid.innerHTML += `
            <div class="cal-day ${highlightClass}" data-date="${dateString}">
                <strong>${day}</strong>
                ${badgeHtml}
            </div>
        `;
    }
}

// Function to fetch frequencies and populate the dropdown
async function loadFrequencies() {
    /*
    Loads options to frequency select to filter with
     */
    const freqSelect = document.getElementById('freq-filter');
    const codeSelect = document.getElementById('code-filter');

    // Safety check: Make sure the select element actually exists on this page
    if (!freqSelect) return;

    try {
        // Fetch distinct frequencies from server
        const response = await fetch('/api/get_freqs_codes');

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        // Parse the JSON response
        const data = await response.json();

        // Loop through the array inside the 'frequencies' key
        data.freq_list.forEach(frequency => {
            // Create a new <option> element
            const option = document.createElement('option');

            // Set the value that will be sent to the server
            option.value = frequency;

            // Format the text the user actually sees
            option.textContent = `${frequency.toFixed(3)} MHz`;

            // Attach the new option to your select element
            freqSelect.appendChild(option);
        });

        data.code_list.forEach(code => {
            // Create a new option element
            const option = document.createElement('option');

            // Set the value that will be sent to the server
            option.value = code;

            // Format the text the user actually sees
            option.textContent = code;

            // Attach the new option to your select element
            codeSelect.appendChild(option);
        });

    } catch (error) {
        console.error("Failed to load frequencies:", error);

        // Let the user know it failed
        const errorOption = document.createElement('option');
        errorOption.value = "";
        errorOption.textContent = "Error loading frequencies";
        errorOption.disabled = true;
        freqSelect.appendChild(errorOption);
    }
}

// Button Listeners to change months
document.getElementById('prev-month').addEventListener('click', () => {
    currentMonth--;
    if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    renderCalendar(currentYear, currentMonth);
    loadMonthlyChart(currentYear, currentMonth);
});

document.getElementById('next-month').addEventListener('click', () => {
    currentMonth++;
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    renderCalendar(currentYear, currentMonth);
    loadMonthlyChart(currentYear, currentMonth);
});

calendarGrid.addEventListener('click', (event) => {
    /*
    Calendar grid click listener
     */
    const clickedDay = event.target.closest('.cal-day'); // Get clicked day element
    if (!clickedDay) return;

    activeFilterDate = clickedDay.getAttribute('data-date'); // Set selected day
    loadDailyChart(activeFilterDate); // Render hourly average SNR chart
    document.getElementById('selected-day-message').style.display = "flex"; // Show selected day text
    document.getElementById('selectedDay').innerHTML = `${activeFilterDate}`;

    // Highlight the clicked day
    document.querySelectorAll('.cal-day').forEach(day => {
        // Removed previously selected day (if there was any)
        day.classList.remove('bg-primary', 'text-white');
    });
    clickedDay.classList.add('bg-primary', 'text-white');

    // Show the "Clear Selection" button
    clearButton.style.display = 'block';

    const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
    currentPage = 1; // Reset page number
    get_recs(apiSortKey); // Reload data table
});

// Update the Clear Button Listener
clearButton.addEventListener('click', () => {
    activeFilterDate = null; // Unselect day
    activeFilterHour = null; // Unselect hour
    document.getElementById('selectedDayText').innerHTML = "selected day";
    document.getElementById('selected-day-message').style.display = "none"; // Hide selected day message
    loadDailyChart(activeFilterDate); // Re-render hourly average SNR chart

    // Remove highlight from all calendar days
    document.querySelectorAll('.cal-day').forEach(day => {
        day.classList.remove('bg-primary', 'text-white');
    });

    // Hide the clear button again
    clearButton.style.display = 'none';

    const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
    currentPage = 1; // Reset page number
    get_recs(apiSortKey); // Reload data in the table
});

document.querySelectorAll('.prev-page-btn').forEach(btn => {
    /*
    Load previous page
     */
    btn.addEventListener('click', function() {
        currentPage--;
        const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
        get_recs(apiSortKey);
    });
});

document.querySelectorAll('.next-page-btn').forEach(btn => {
    /*
    Load next page
     */
    btn.addEventListener('click', function() {
        currentPage++;
        const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
        get_recs(apiSortKey);
    });
});

// Event listener for data refresh button
document.getElementById('reload-table-btn').addEventListener('click', async function() {
    const btn = this;
    const originalText = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = `
        <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        Refreshing...
    `;

    try {
        const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
        await get_recs(apiSortKey); // Reload table
        loadMonthlyChart(currentYear, currentMonth); // Reload daily average SNR chart
        if(activeFilterDate){
            // If a day was selected, reload hourly SNR chart
            loadDailyChart(activeFilterDate);
        }

    } catch (error) {
        console.error("Error reloading table data:", error);
        alert("Failed to refresh data. Please try again.");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
    renderCalendar(currentYear, currentMonth, activeFilterDate); // Reload recording counts in calendar grid
});

document.getElementById('time-filter').addEventListener('change', async function() {
    /*
    Time filter select element changed
     */
    try {
        let selectedHour = document.getElementById('time-filter').value; // Get selected hour
        if(selectedHour === ""){
            // If no hour was selected (option "-"), disable filter
            activeFilterHour = null;
        }
        else{
            // Enable hour filter
            activeFilterHour = selectedHour;
        }
        const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
        await get_recs(apiSortKey); // Reload table data

    } catch (error) {
        console.error("Error loading table data:", error);
        alert("Failed to refresh data. Please try again.");
    }
});

// Delete button listener
document.addEventListener('click', async function(event) {
    // Check if the clicked element (or its parent) has the 'deleteBtn' class
    if (event.target.classList.contains('deleteBtn')) {
        const btn = event.target;

        // Grab the specific file path from the button's data attribute
        const filePath = btn.dataset.filepath;

        // Confirm dialog (to prevent accidental deletions)
        if (!confirm('Are you sure you want to permanently delete this file?')) {
            return;
        }

        // Show loading state
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
        btn.disabled = true;

        try {
            // Send the request
            const url = `/api/delete_file?file_path=${encodeURIComponent(filePath)}`;
            const response = await fetch(url);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Server responded with ${errorData.error}`);
            }

            // Success: remove the entire row from the table
            btn.closest('tr').remove();

        } catch (error) {
            console.error("Failed to delete file:", error);
            alert("Error: Could not delete the file. Check the server logs.");

            // Reset the button if it failed
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }
});

document.querySelectorAll('.jump-to-page-input').forEach(input => {
    /*
    Add event listener to both page navigations
     */
    input.addEventListener('change', function(e) {
        /*
        User typed a page number to number page input
         */
        let targetPage = parseInt(e.target.value);

        if (targetPage >= 1 && targetPage <= totalPages) {
            // If page is in total page range
            currentPage = targetPage; // Set current page
            const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
            get_recs(apiSortKey); // Realod the table
        } else {
            e.target.value = currentPage;
        }
    });
});

document.getElementById('freq-filter').addEventListener('change', function (){
    /*
    Frequency filter changed
     */
    selectedFreq = this.value;
    const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
    get_recs(apiSortKey);
});

document.getElementById('code-filter').addEventListener('change', function (){
    /*
    Airport code filter changed
     */
    selectedCode = this.value;
    const apiSortKey = isDescending ? `-${currentSortColumn}` : currentSortColumn;
    get_recs(apiSortKey);
});

// Load the initial calendar on page load
const urlParams = new URLSearchParams(window.location.search);
const targetDate = urlParams.get('date'); // Select a day from URL params
const targetYear = urlParams.get('year'); // Set year from URL params
const targetMonth = urlParams.get('month'); // Set month from URL params
if(targetDate){
    activeFilterDate = targetDate; // Enable date filter
    clearButton.style.display = 'block'; // Show clear button
}
if(targetYear){
    currentYear = targetYear; // Set specified year
}
if(targetMonth){
    currentMonth = parseInt(targetMonth, 10).toString(); // Set specified month
}

renderCalendar(currentYear, currentMonth, activeFilterDate); // Initialize the calendar grid
get_recs('-date'); // Initialize the recordings table

document.addEventListener('DOMContentLoaded', () => {
    // Set input default values
    const monthSelector = document.getElementById('month-select');
    const yearSelector = document.getElementById('year-select');

    // Load initial charts
    loadMonthlyChart(yearSelector.value, monthSelector.value);
    if(activeFilterDate){
        // If a date was specified, loud hourly average SNR chart
        loadDailyChart(activeFilterDate);
        document.getElementById('selected-day-message').style.display = "flex";
        document.getElementById('selectedDay').innerHTML = `${activeFilterDate}`;
    }
    else{
        document.getElementById('not-selected-message').style.display = "block";
        document.getElementById('empty-message-day').style.display = "none";
        document.getElementById('dailyChart').style.display = "none";
    }

    monthSelector.addEventListener('change', (e) => {
        /*
        Reload daily average SNR chart when month changes
         */
        loadMonthlyChart(currentYear, currentMonth);
    });

    yearSelector.addEventListener('change', (e) => {
        /*
        Reload daily average SNR when year changed
         */
        loadMonthlyChart(currentYear, currentMonth);
    });

    loadFrequencies(); // Load frequency options
});
