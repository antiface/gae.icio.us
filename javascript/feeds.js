function setnotify (id, notify) {
    $.ajax({
        url: "/setnotify",
        data: { feed: id, notify: notify}
    })
}

function get_tags (id) {
    $("#dashboard").html('<a>Associate a tag to the feed</a>');
    $.ajax({
        url: "/gettagsfeed",
        data: { feed: id},
        success: function(html) {
            $("#comment-"+id).html(html);
        } 
    })
}

function del_feed (id) {
    $("#dashboard").html('<a>Deleting the feed</a>');
    $.ajax({
        url: "/feed",
        data: { id: id},
        success: function() {
            $("#dashboard").html('<a>OK. Feed deleted</a>');
            $("#row-"+id).addClass('hide');
        } 
    })
}

function sync_feed (id) {
    $("#dashboard").html('<a>Sync the feed</a>');
    $.ajax({
        url: "/checkfeed",
        data: { feed: id},
        success: function() {
            $("#dashboard").html('<a>OK sync started </a>');
        } 
    })
}

$('#tips-feed').bind('close', function () {
    $.cookie('tips-feed', 'hide'); 
})

$('#bookmarklet').tooltip()