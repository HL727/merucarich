class Utils {
    
    static dialog(title, message) {
	$('#dialog > p').text(message);
	$("#dialog").dialog({
	    modal:true, 
	    title: title,
	    buttons: {
		"確認": function() {
		    $(this).dialog("close");
		}
	    }
	});
    }

    static selectYahoo() {
	$(".dropdown1").addClass("active");
    }

    static selectMercari() {
	$(".dropdown2").addClass("active");
    }
    
    static selectAmazonSetting() {
	$(".dropdown3").addClass("active");
    }

}
