class AmazonCategory {

    // -- 大カテゴリー用
    
    // 選択可能なカテゴリー
    static setSelectableCategory() {
	AmazonCategory.setSelect('#selectable', '/api/amazon_category/?format=json');
    }
    
    // 選択済みカテゴリー
    static setSelectedCategory() {
	AmazonCategory.setSelect('#selected', '/api/amazon_category_user/?format=json');
    }

    // -- 詳細カテゴリー用

    
    static setSelectedParentCategory() {
	AmazonCategory.setSelect('#selected_parent_category', '/api/amazon_category_user/?format=json');
	$('#selected_parent_category').prepend($('<option></option>').attr('value', '').text('選択してください。'));
    }

    static onChangeSelectedParentCategory() {
	var val = $('#selected_parent_category').val();
	$("#category").val(val);
	// 左側
	AmazonCategory.setSelect('#selectable', '/api/amazon_child_category/?format=json&category=' + val);
	// 右側
	AmazonCategory.setSelect('#selected', '/api/amazon_child_category_user/?format=json&category=' + val);
	// ボタンの活性制御
	var enable = (val === '');
	$("#submit").prop("disabled", enable);
    }

    // -- 以下、共通
    
    // 選択済みカテゴリーの全アイテムを選択
    static selectAllSelectedCategory() {
	$('select#selected option').prop('selected', true);
    }

    // リスト取得
    static setSelect(dom_id, url) {
	var dropdown = $(dom_id);
	dropdown.empty();
	$.getJSON(url, function (data) {
	    $.each(data, function (key, entry) {
		dropdown.append($('<option></option>').attr('value', entry.value).attr('id', entry.value).text(entry.name));
	    })
	});
    }

}
