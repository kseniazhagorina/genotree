function initCarouselFullScreenIn(container) {

    // для всех элементов с классом .carousel.full-screen
    // установить корректный размер
    var item = $(container).find('.carousel.full-screen .item');
    var wHeight = $(window).height();
    item.height(wHeight);
    $(window).on('resize', function (){
      wHeight = $(window).height();
      item.height(wHeight);
    });

    container.find('.modal.carousel.full-screen').on('shown.bs.modal', function() {
        $(this).css('background-image', 'url(/static/img/carousel_background.jpg)');
        loadLazyContent($(this));
        yaGoals.open_photo_gallery();
        $(this).carousel('pause');
    })
}