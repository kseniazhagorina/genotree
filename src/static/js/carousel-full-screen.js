function initCarouselFullScreenIn(container) {
    // �������������� (����������� ������, ��������� ������� � ��.)
    // ��� ���� �������� ������� ����� .carousel.full-screen
    
    // �������� � ������ ������� ������
    var item = $(container).find('.carousel.full-screen .item'); 
    var wHeight = $(window).height();
    item.height(wHeight);
    $(window).on('resize', function (){
      wHeight = $(window).height();
      item.height(wHeight);
    });
    
    // �������� �������� �������� � ��������� �����
    container.find('.modal.carousel.full-screen').on('shown.bs.modal', function() {
        $(this).css('background-image', 'url(/static/carousel_background.jpg)');
        loadLazyContent($(this));
        yaGoals.open_photo_gallery();
        $(this).carousel('pause');
    })
}    