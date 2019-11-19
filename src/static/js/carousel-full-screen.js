function initCarouselFullScreenIn(container) {
    // инициализирует (настраивает размер, обработку событий и пр.)
    // для всех объектов имеющих класс .carousel.full-screen
    
    // карусель в режиме полного экрана
    var item = $(container).find('.carousel.full-screen .item'); 
    var wHeight = $(window).height();
    item.height(wHeight);
    $(window).on('resize', function (){
      wHeight = $(window).height();
      item.height(wHeight);
    });
    
    // загрузка ленивого контента в модальных окнах
    container.find('.modal.carousel.full-screen').on('shown.bs.modal', function() {
        $(this).css('background-image', 'url(/static/carousel_background.jpg)');
        loadLazyContent($(this));
        yaGoals.open_photo_gallery();
        $(this).carousel('pause');
    })
}    