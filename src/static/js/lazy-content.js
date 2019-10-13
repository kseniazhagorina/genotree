// загружает фотографии имеющие аттрибут lazy-src
function loadLazyContent(container) {
    container.find('img[lazy-src]').each(function(){
        var img = $(this);
        img.attr("src", img.attr("lazy-src"));
        img.removeAttr("lazy-src");
    });
}

function loadLazyContentSvg(container) {
    container.find('image[lazy-href]').each(function(){
        var img = $(this);
        img.attr("href", img.attr("lazy-href"));
        img.removeAttr("lazy-href");
    });
}