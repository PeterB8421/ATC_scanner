function get_recs(sortKey){
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
            console.log(data) // DEBUG

            if(data.length === 0){
                document.getElementById('rec-table').innerText = "There are no recordings yet.";
            }
            else{
                const tableEl = document.getElementById('rec-table-content');
                tableEl.innerHTML = "";

                const rows = data.map(rec => {
                    return `
                        <tr>
                            <td><a href="${rec.abs_url}">${rec.file_name}</a></td>
                            <td> <audio controls><source src="${rec.file_path}"></audio> </td>
                            <td>${rec.snr}</td>
                            <td>${rec.duration} s</td>
                            <td>${rec.date}</td>
                            <td><a class="btn btn-primary" href="${rec.abs_url}">Detail</a></td>
                        </tr>
                    `;
                }).join('');
                tableEl.innerHTML = rows;
            }
        })
        .catch(error => {
            console.error('Failed to fetch recordings!')

            if(error.error){
                console.error(`API error: ${error.error}`)
            }
            else{
                console.error('Network error occurred!')
            }
        })
}

get_recs('newest');
