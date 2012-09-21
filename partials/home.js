$(document).ready(function() {

  $("#star-{{ bm.id }}").click(function() {
    $.ajax({
      url: "/star",
      data: { bm: "{{ bm.id }}" },
      success: function(html) {
        $("#dashboard").html('<a>Star status changed</a>');
        $("#star-{{ bm.id }}").html(html);
      }
    });
  })

  $("#share-{{ bm.id }}").click(function() {
    $.ajax({
      url: "/share",
      data: { bm: "{{ bm.id }}" },
      success: function(html) {
        $("#dashboard").html('<a>Share status changed</a>');
        $("#share-{{ bm.id }}").html(html);
      }
    });
  })

  $("#prev-{{ bm.id }}").toggle(  
    function() {
      $.ajax({
        url: "/getcomment",
        data: { bm: "{{ bm.id }}" },
        success: function(html) {
          $("#comment-{{ bm.id }}").html(html);
        }
      });
    },
    function() {
      $("#comment-{{ bm.id }}").html('');
        }
  )

  $("#tags-butt-{{ bm.id }}").toggle(
    function() {
      $("#dashboard").html('<a>Select a new tag</a>');
      $.ajax({
        url: "/gettags",
        data: { bm: "{{ bm.id }}" },
        success: function(html) {
          $("#comment-{{ bm.id }}").html(html);
        }
      });
    },
    function() {
      $("#comment-{{ bm.id }}").html('');
        }
  )

  $("#edit-{{ bm.id }}").toggle(
    function() {
      $.ajax({
        url: "/getedit",
        data: { bm: "{{ bm.id }}" },
        success: function(html) {
          $("#dashboard").html('<a>Edit the item</a>');
          $("#comment-{{ bm.id }}").html(html);
        }
      });
    },
    function() {
      $("#comment-{{ bm.id }}").html('');
        }
  )

  $("#arch-{{ bm.id }}").click(function() {
    $.ajax({
      url: "/archive",
      data: { bm: "{{ bm.id }}" },
      success: function() {
        $("#dashboard").html('<a>Bookmark archived</a>');
        $("#row-{{ bm.id }}").addClass('hide');
      },
    });
  })

  $("#trash-{{ bm.id }}").click(function() {
    $.ajax({
      url: "/trash",
      data: { bm: "{{ bm.id }}" },
      success: function() {
        $("#dashboard").html('<a>Bookmark deleted</a>');
        $("#row-{{ bm.id }}").addClass('hide');
      },
    });
  })
});
