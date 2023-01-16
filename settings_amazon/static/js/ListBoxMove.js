// @see https://dennie.tokyo/web/2016/07/23/listboxmove/

//イベント
$(function() {
    //右へ要素を追加する。
    $('#left-btn').click(rightMove);
    
    //カテゴリ削除イベント
    $('#right-btn').click(leftMove);
});
 
//右へ要素を追加する。
function rightMove() {
    
    //左リストで選択している要素のIDを取得する。
    value = $("#selectable").children("option:selected").val();
 
    //要素が選択されている場合、以下を行う。
    if(value !== void 0){
 
        //左リストで選択している要素を取得する。
        element = $("#selectable").children("option:selected").html();
 
        //選択した要素を左リストから削除する。
        $("#" + value).remove();
 
        //選択した要素を、右リストへ追加する。
        $("#selected").append('<option value = ' + value + ' id = ' + value + '>' + element + '</option>');
        
        //選択状態を開放する。
        //$("#selected").removeAttr("option:selected");
    }
}


//https://stackoverflow.com/questions/15190464/how-do-i-post-all-options-in-a-select-list


//左へ要素を追加する。
function leftMove() {
    
    //右リストで選択している要素のIDを取得する。
    value = $("#selected").children("option:selected").val();
 
    //要素が選択されている場合、以下を行う。
    if(value !== void 0){
 
        //右リストで選択している要素を取得する。
        element = $("#selected").children("option:selected").html();
 
        //選択した要素を右リストから削除する。
        $("#" + value).remove();
 
        //選択した要素を、左リストへ追加する。
        $("#selectable").append('<option value = ' + value + ' id = ' + value + '>' + element + '</option>');
        
        //選択状態を開放する。
        //$("#selectable").removeAttr("option:selected");
    }
}
