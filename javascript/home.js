function archive (id) {
    $.ajax({
        url: "/archive",
        data: { bm: id },
        success: function() {
            $("#dashboard").html('<a>Archived status changed</a>');
            $("#row-"+id).addClass('hide');
        } }); }

function trash (id) {
    $.ajax({
        url: "/trash",
        data: { bm: id },
        success: function() {
            $("#dashboard").html('<a>Trashed status changed</a>');
            $("#row-"+id).addClass('hide');
        } }); }

function star (id) {
    $.ajax({
        url: "/star",
        data: { bm: id },
        success: function(html) {
            $("#dashboard").html('<a>Star status changed</a>');
            $("#star-"+id).html(html);
        } }); }

function share (id) {
    $.ajax({
        url: "/share",
        data: { bm: id },
        success: function(html) {
            $("#dashboard").html('<a>Share status changed</a>');
            $("#share-"+id).html(html);
        } }); }

function comment (id) {
    $.ajax({
        url: "/getcomment",
        data: { bm: id },
        success: function(html) {
            $("#comment-"+id).html(html);
        } }); }

function tags (id) {
    $("#dashboard").html('<a>Select a new tag</a>');
    $.ajax({
        url: "/gettags",
        data: { bm: id },
        success: function(html) {
            $("#comment-"+id).html(html);
        } }); }
    
function edit (id) {
    $.ajax({
        url: "/getedit",
        data: { bm: id },
        success: function(html) {
            $("#dashboard").html('<a>Edit the item</a>');
            $("#comment-"+id).html(html);
        } }); }