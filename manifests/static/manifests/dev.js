$(function() {
  // Localize & shorthand django vars
  var l = window.harvard_md_server;

  // Compile Handlebars templates into t
  var t = {};
  $('script[type="text/x-handlebars-template"]').each(function () {
    t[this.id] = Handlebars.compile(this.innerHTML);
  });

  //print form

  var printPDF = function(btn, event){
    var d_id = $("#drs_id").val();
    var url = l.PDS_PRINT_URL + d_id;
    var xmlhttp;
    var focusType = window.currentFocus,
        n = window.focusModules[focusType].currentImgIndex + 1;
    if (window.XMLHttpRequest) {// code for IE7+, Firefox, Chrome, Opera, Safari
      xmlhttp=new XMLHttpRequest();
    }
    else {// code for IE6, IE5
      xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
    }
    var $dialog = $('#print-tmpl');

    var printMode = $("#printOpt").val();
    var email = $("#email").val();
    var start = $("#start").val();
    var end = $("#end").val();
    if (printMode === "current") {
      u = u + '?n=' + n +'&printOpt=single';
      window.open(u,'');
      $dialog.close();

    } else if (printMode === "range") {
      u = u + '&printOpt=range' + '&start=' + start +
        '&end=' + end + '&email=' + email;
      xmlhttp.open('GET',u,true);
      xmlhttp.send();
      $dialog.close();

    } else  { //all
      u = u + '&printOpt=range' + '&start=' + start +
        '&end=' + end + '&email=' + email;
      xmlhttp.open('GET',u,true);
      xmlhttp.send();
      $dialog.close();
    }
  };



  $( "#print" ).submit(function( event ) {
    //alert( "Handler for .submit() called." );
    printPdf(event);
    event.preventDefault();
  });

  $( "#pdssubmit" ).click(function() {
    $( "#print" ).submit();
  });

  Mirador({
    "id": "viewer",
    "layout": l.LAYOUT,
    "saveSession": false,
    "mainMenuSettings" : {
      "buttons": { bookmark: false},
      "userButtons": [
        {"label": "Help",
         "iconClass": "fa fa-question-circle",
         "attributes": { "id": "help", "href": "http://nrs.harvard.edu/urn-3:hul.ois:hlviewerhelp"}},
        {"label": "View in PDS",
         "iconClass": "fa fa-external-link",
         "attributes": { "id": "view-in-pds", "href": "#no-op"}},
        {"label": "Cite",
         "iconClass": "fa fa-quote-left",
         "attributes": { "id": "cite", "href": "#no-op"}},
        {"label": "Search",
         "iconClass": "fa fa-search",
         "attributes": { "id": "search", "href": "#no-op"}},
        {"label": "Print",
         "iconClass": "fa fa-print",
         "attributes": { "id": "print", "href": "#no-op"}},

      ],
    	"userLogo": {
        "label": "Harvard Library",
        "attributes": { "id": "harvard-bug", "href": "http://lib.harvard.edu"}}
    },

    "data": l.MIRADOR_DATA,
    "windowObjects": l.MIRADOR_WOBJECTS
  });

  var present_choices = function (e) {
    e.preventDefault();
    var op = e.currentTarget.id;
    var choices = $.map(Mirador.viewer.workspace.windows, function (window, i) {
      var uri = window.manifest.uri,
          parts = uri.split("/"),
          last_idx = parts.length - 1,
          drs_match = parts[last_idx].match(/drs:(\d+)/),
          drs_id = drs_match && drs_match[1],
          focusType = window.currentFocus,
          n = window.focusModules[focusType].currentImgIndex + 1;
      if (drs_match) {
        return {"label": window.manifest.jsonLd.label, "drs_id": drs_id, "uri": window.manifest.uri, "n": n};
      }
      // else omit manifest because we don't know how to cite/view it
    });
    if (choices.length == 1) {
      operations[op](choices[0].drs_id, choices[0].n);
    }
    else {
      var $dialog = $('#choice-modal');
      if ($dialog.get().length > 0) {
        $dialog.dialog('close');
      }
      else if (choices.length) {
        $dialog = $('<div id="choice-modal" style="display:none" />');
        $dialog.html(t['choices-tmpl']({choices: choices, op: op}));
        $dialog.appendTo('body');
        $dialog.dialog({modal: true,
                        draggable: false,
                        resizable: false,
                        width: "90%",
                        classes: "qtip-bootstrap",
                        title: "Citation",
                        close: function (e) { $(this).remove()}
                       }).dialog('open');
        $dialog.find('a').on('click', function (e) {
          e.preventDefault();
          $dialog.dialog('close');
          operations[op]($(e.currentTarget).data('drs-id'), $(e.currentTarget).data('n'));
        });
      }
    }
  };
  var operations = {
    "view-in-pds": function (drs_id, n) {
      window.open(l.PDS_VIEW_URL + drs_id + "?n=" + n);
    },
    "cite": function (drs_id, n) {
      var $dialog = $('#citation-modal');

      if ($dialog.get().length > 0) {
        $dialog.dialog('close');
      }
      else {
        $dialog = $('<div id="citation-modal" style="display:none" />');
        $.getJSON('//pdstest.lib.harvard.edu:9005/pds/cite/' + drs_id + '?callback=?', {'n':n})
          .done(function (data) {
            if (data.citation) {
              $dialog.html(t['citation-tmpl'](data.citation));
              $dialog.appendTo('body');
              $dialog.dialog({modal: true,
                              draggable: false,
                              resizable: false,
                              width: "90%",
                              classes: "qtip-bootstrap",
                              title: "Citation",
                              close: function (e) { $(this).remove()}
                             }).dialog('open');
            } //TODO: Else graceful error display
          });
      }
    },
    "search": function(drs_id, n) {
      var content = { drs_id: drs_id, n: n };
      var $dialog = $('#search-modal');
      if ($dialog.get().length > 0) {
        $dialog.dialog('close');
      }
      else {
        $dialog = $('<div id="search-modal" style="display:none" />');
        $dialog.html(t['search-tmpl'](content));
        $dialog.dialog({modal: true,
                        draggable: false,
                        resizable: false,
                        width: "90%",
                        classes: "qtip-bootstrap",
                        title: "Search Manifest",
                        close: function (e) { $(this).remove()}
                       }).dialog('open');
      }
    },
    "print": function(drs_id, n) {
      console.log("print" + drs_id);
      var content = { drs_id: drs_id, n: n };
      var $dialog = $('#print-modal');

      if ($dialog.get().length > 0) {
        $dialog.dialog('close');
      }
      else {
        $dialog = $('<div id="print-modal" style="display:none" />');
        $dialog.html(t['print-tmpl'](content));
        $dialog.dialog({modal: true,
                        draggable: false,
                        resizable: false,
                        width: "90%",
                        classes: "qtip-bootstrap",
                        title: "Print Manifest",
                        close: function (e) { $(this).remove()}
                       }).dialog('open');
      }
    }
  };

  $(document).on('click', "#cite, #view-in-pds, #search, #print", present_choices);
});
