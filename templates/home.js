$(document).ready(function() {

  $("#star-{{ bm.key.id() }}").click(function() {
    $.ajax({
      url: "/star",
      data: { bm: "{{ bm.key.id() }}" },
      success: function(html) {
        $("#dashboard").html('<a>Star status changed</a>');
        $("#star-{{ bm.key.id() }}").html(html);
      }
    });
  })

  $("#prev-{{ bm.key.id() }}").toggle(  
    function() {
      $.ajax({
        url: "/getcomment",
        data: { bm: "{{ bm.key.id() }}" },
        success: function(html) {
          $("#comment-{{ bm.key.id() }}").html(html);
        }
      });
    },
    function() {
      $("#comment-{{ bm.key.id() }}").html('');
        }
  )

  $("#tags-butt-{{ bm.key.id() }}").toggle(
    function() {
      $("#dashboard").html('<a>Select a new tag</a>');
      $.ajax({
        url: "/gettags",
        data: { bm: "{{ bm.key.id() }}" },
        success: function(html) {
          $("#comment-{{ bm.key.id() }}").html(html);
        }
      });
    },
    function() {
      $("#comment-{{ bm.key.id() }}").html('');
        }
  )

  $("#edit-{{ bm.key.id() }}").toggle(
    function() {
      $.ajax({
        url: "/getedit",
        data: { bm: "{{ bm.key.id() }}" },
        success: function(html) {
          $("#dashboard").html('<a>Edit the item</a>');
          $("#comment-{{ bm.key.id() }}").html(html);
        }
      });
    },
    function() {
      $("#comment-{{ bm.key.id() }}").html('');
        }
  )

  $("#arch-{{ bm.key.id() }}").click(function() {
    $.ajax({
      url: "/archive",
      data: { bm: "{{ bm.key.id() }}" },
      success: function() {
        $("#dashboard").html('<a>Bookmark archived</a>');
        $("#row-{{ bm.key.id() }}").addClass('hide');
      },
    });
  })

  $("#trash-{{ bm.key.id() }}").click(function() {
    $.ajax({
      url: "/trash",
      data: { bm: "{{ bm.key.id() }}" },
      success: function() {
        $("#dashboard").html('<a>Bookmark deleted</a>');
        $("#row-{{ bm.key.id() }}").addClass('hide');
      },
    });
  })
});
