$("#n-w-{{ feed.id }}").click(function() {
    $.ajax({
        url: "/setnotify",
        data: { feed: '{{ feed.id }}', notify: 'web'}
    })
})
$("#n-e-{{ feed.id }}").click(function() {
    $.ajax({
        url: "/setnotify",
        data: { feed: '{{ feed.id }}', notify: 'email'}
    })
})
$("#n-d-{{ feed.id }}").click(function() {
    $.ajax({
        url: "/setnotify",
        data: { feed: '{{ feed.id }}', notify: 'digest'}
    })
})


$("#tags-{{ feed.id }}").toggle(
    function() {
        $("#dashboard").html('<a>Associate a tag to the feed</a>');
        $.ajax({
            url: "/gettagsfeed", 
            data: {feed: '{{ feed.id }}'}, 
            success: function(html) {
                $("#comment-{{ feed.id }}").html(html);
            } 
        })
    },
    function() {
        $("#dashboard").html('<a>ok.</a>');
        $("#comment-{{ feed.id }}").addClass('hide'); 
    }
)



if ($.cookie('tips-feed') == 'hide') {
    $("#tips-feed").addClass('hide');
}
$('#tips-feed').bind('close', function () {
    $.cookie('tips-feed', 'hide'); 
})


$("#delete-{{ feed.id }}").click(function(){
    $("#dashboard").html('<a>Deleting the feed</a>');
    $.ajax({
        url: "/feed",
        data: { id: "{{ feed.id }}" },
        success: function() {
            $("#dashboard").html('<a>OK. Feed deleted</a>');
            $("#row-{{ feed.id }}").addClass('hide');
        }
    });
});
$("#refresh-{{ feed.id }}").click(function(){
    $("#dashboard").html('<a>Refresh the feed</a>');
    $.ajax({
        url: "/checkfeed",
        data: { feed: "{{ feed.id }}" },
        success: function() {
            $("#dashboard").html('<a>OK check started </a>');
        }
    });
});