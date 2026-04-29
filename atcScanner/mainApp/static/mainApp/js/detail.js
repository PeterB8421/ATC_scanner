/*
Author: Bc. Petr Balok
 */
import WaveSurfer from 'https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.esm.js'
import Spectrogram from 'https://unpkg.com/wavesurfer.js@7/dist/plugins/spectrogram.esm.js'

function createGraphs(){
    const audioEl = document.querySelector("audio");
    const graphEl = document.querySelector("#graphs");

    const ws = WaveSurfer.create({
        container: graphEl,
        media: audioEl,
        height: 100,
        interact: true,
        plugins: [
            Spectrogram.create({
                labels: true,
                height: 100,
            }),
        ],
    })
}

createGraphs();
