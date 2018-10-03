$(function() {
    $('#addComment').click(function() {
        data = []
        comment = $('#userComment').val()
        agentid = $('#addComment').attr('data-agentid')
        data.push(comment,agentid)
        $.ajax({
            url: '/addcomment',
            data: JSON.stringify(data),
            contentType: 'application/json',
            type: 'POST',
            success: function(response) {
                console.log(response);
                location.reload()
            },
            error: function(error) {
                console.log(error);
            }
        });
    });      
});
