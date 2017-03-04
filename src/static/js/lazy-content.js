// загружает фотографии имеющие аттрибут lazy-src
function loadLazyContent(container) {
    container.find('img[lazy-src]').each(function(){
        var img = $(this);
        img.attr("src", img.attr("lazy-src"));
        img.removeAttr("lazy-src");
    });
}