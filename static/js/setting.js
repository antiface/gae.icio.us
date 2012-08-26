$(document).ready(function() {
  if ($.cookie('mys') == 'True') {
    $("#mys-test").html('<i class="icon-thumbs-up"></i> <strong>Enabled </strong>');
    $("#mys-check").prop("checked", true);
  } else {
    $("#mys-test").html('<i class="icon-thumbs-down"></i> <strong>Disabled</strong>');  
    $("#mys-check").prop("checked", false);
  }

  if ($.cookie('daily') == 'True') {
    $("#daily-test").html('<i class="icon-thumbs-up"></i> <strong>Enabled </strong>');
    $("#daily-check").prop("checked", true);
  } else {
    $("#daily-test").html('<i class="icon-thumbs-down"></i> <strong>Disabled</strong>');  
    $("#daily-check").prop("checked", false);
  }

  if ($.cookie('twitt') == 'True') {
    $("#twitt-test").html('<i class="icon-thumbs-up"></i> <strong>Enabled </strong>');
    $("#twitt-check").prop("checked", true);
  } else {
    $("#twitt-test").html('<i class="icon-thumbs-down"></i> <strong>Disabled</strong>');  
    $("#twitt-check").prop("checked", false);
  }
})


$("#mys-check").change(function() {
  $.ajax({
    url: "/setmys",
    success: function(html) {          
    $("#mys-test").html(html);
    }
  })
})

$("#daily-check").change(function() {
  $.ajax({
    url: "/setdaily",
    success: function(html) {          
    $("#daily-test").html(html);
    }
  })
})

$("#twitt-check").change(function() {
  $.ajax({
    url: "/settwitt",
    success: function(html) {          
    $("#twitt-test").html(html);
    }
  })
})