function initCarouselFullScreen() {
    // �������������� (����������� ������, ��������� ������� � ��.)
    // ��� ���� �������� ������� ����� .carousel.full-screen
    $(document).ready(function() {
        // �������� � ������ ������� ������
        var $item = $('.carousel.full-screen .item'); 
        var $wHeight = $(window).height();
        $item.height($wHeight);
        $(window).on('resize', function (){
          $wHeight = $(window).height();
          $item.height($wHeight);
        });
        
        // �������� �������� �������� � ��������� �����
        $('.modal.carousel.full-screen').on('shown.bs.modal', function() {
            loadLazyContent($(this));
            yaGoals.open_photo_gallery();
        })

        // ������ ����������
        //$('.carousel').carousel({
        //  interval: 5000,
        //  pause: "true"
        //});
    });
}    