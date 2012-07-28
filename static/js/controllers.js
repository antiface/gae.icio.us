function calcoli($scope, $http) {
  $http.get('http://demo.metrico.org/ribassoajax?cmek=ag1zfm1ldHJpY28tb3JnchYLEg5Db21wdXRvTWV0cmljbxjhswoM').success(function(data) {
    $scope.ribassi = data;
  });
}
 
//calcoli.$inject = ['$scope', '$http'];