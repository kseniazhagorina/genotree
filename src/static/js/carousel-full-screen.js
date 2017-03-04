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
        $('.modal').on('shown.bs.modal', function() {
            loadLazyContent($(this));
        })

        // ������ ����������
        //$('.carousel').carousel({
        //  interval: 5000,
        //  pause: "true"
        //});
    });
}    