$(function () {
  // 获取修改之前的值
  let noModifyIsStaff = $("input[name='login_admin']:checked").val();
  let noModifyIsSuperuser = $("input[name='is_superuser']:checked").val();
  let noModifyIsActive = $("input[name='is_active']:checked").val();
  let noModifyGroups = $("#add_group").val();

  // ================== 删除用户 ================
  let $userDel = $(".btn-del");  // 1. 获取删除按钮
  $userDel.click(function () {   // 2. 点击触发事件
    let _this = this;
    let sUserId = $(this).parents('tr').data('id');
    let sUserName = $(this).parents('tr').data('name');

    fAlert.alertConfirm({
      title: `确定删除 ${sUserName} 这个用户吗？`,
      type: "error",
      confirmText: "确认删除",
      cancelText: "取消删除",
      confirmCallback: function confirmCallback() {

        $.ajax({
          url: "/admin/users/" + sUserId + "/",  // url尾部需要添加/
          // 请求方式
          type: "DELETE",
          dataType: "json",
        })
          .done(function (res) {
            if (res.errno === "0") {
              message.showSuccess("用户删除成功");
              $(_this).parents('tr').remove();
            } else {
              swal.showInputError(res.errmsg);
            }
          })
          .fail(function () {
            message.showError('服务器超时，请重试！');
          });
      }
    });
  });


});
