document.onkeydown = function (e) {
    e = e || window.event;
    if (e.keyCode == '37') { //left
        document.getElementById('prev-page').click();
    }
    else if (e.keyCode == '39') { //right
        document.getElementById('next-page').click();
    }
}

function toggleHeader (header) {
    if (header.style.display == 'block') {
        header.style.display = 'none';
    }
    else {
        header.style.display = 'block';
    }
}

function toggleHeaders (name) {
    var headers = document.getElementsByClassName(name);
    for (var i = 0; i < headers.length; i++) {
        toggleHeader(headers[i]);
    }
}

function toggleAllHeaders () {
    var headers = document.getElementsByClassName('http-headers');
    for (var i = 0; i < headers.length; i++) {
        toggleHeader(headers[i]);
    }
}

function scrollNav (page, count) {
    if (page == 0) {
        pos = 0;
    }
    else if (page == (count - 1)) {
        pos = 1;
    }
    else {
        pos = (page + 1) / count;
    }
    var inner = document.getElementById('nav-inner');
    var outer = document.getElementById('nav-outer');
    var scroll = (inner.scrollWidth - inner.clientWidth) * pos;
    //console.log(inner.scrollWidth, '-', inner.clientWidth, '*', pos, '=', scroll);
    inner.scrollLeft = scroll;
}

function centerNav () {
    var top = document.getElementById('nav-top');
    var scroll = (top.scrollWidth - top.clientWidth) / 2;
    //console.log(top.scrollWidth, '-', top.clientWidth, '/ 2 =', scroll);
    top.scrollLeft = scroll;

    //var bottom = document.getElementById('nav-bottom');
    //bottom.scrollLeft = scroll;
}