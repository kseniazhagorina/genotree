function initCarouselFullScreen() {
    // инициализирует (настраивает размер, обработку событий и пр.)
    // для всех объектов имеющих класс .carousel.full-screen
    $(document).ready(function() {
        // карусель в режиме полного экрана
        var $item = $('.carousel.full-screen .item'); 
        var $wHeight = $(window).height();
        $item.height($wHeight);
        $(window).on('resize', function (){
          $wHeight = $(window).height();
          $item.height($wHeight);
        });
        
        // загрузка ленивого контента в модальных окнах
        $('.modal').on('shown.bs.modal', function() {
            loadLazyContent($(this));
        })

        // запуск карусельки
        //$('.carousel').carousel({
        //  interval: 5000,
        //  pause: "true"
        //});
    });
}    