$(document).ready(function() {

    var tab = $.cookie('active-tab')    

    $('#'+tab).addClass('active');
    if (tab == 'trash') {
        $("#dashboard").html('<a>Trashed items</a>');
        $('#empty_button').removeClass('hide');
    }
    if (tab == 'untagged') {
        $("#dashboard").html('<a>Tagging is important!</a>');
    }
    if (tab == 'inbox') {
        $("#dashboard").html('<a>Welcome to your Inbox</a>');
    }
    if (tab == 'starred') {
        $("#dashboard").html('<a>These are important</a>');
    }
    if (tab == 'shared') {
        $("#dashboard").html('<a>Your shared items</a>');
    }
    if (tab == 'archive') {
        $("#dashboard").html('<a>Your archive</a>');
    }
    if (tab == 'stream') {
        $("#dashboard").html('<a>Our public stream</a>');
    }
    if (tab == 'hero') {
        $("#dashboard").html('<a>Welcome to {{ brand }}</a>');
    }
    if (tab == 'tagcloud') {
        $("#dashboard").html('<a>Your tagcloud</a>');
    }

    $('#addtag').submit(function() {
        var querystring = $(this).serialize();
        event.preventDefault();
        $.ajax({
            url: '/addtag',
            data: querystring,
            success: function() {
                $("#dashboard").html('<a>New tag created</a>');
                $('#addtag input').val('');
                }
            })
        })

$('#bookmarklet').tooltip()

});