pkgname=logv
pkgver=0.1.0
pkgrel=1
pkgdesc="Fast CLI/TUI log viewer for Linux terminals"
arch=('any')
url="https://github.com/example/logv"
license=('MIT')
depends=('python' 'python-rich' 'python-textual' 'python-typer')
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m build --wheel --no-isolation
}

package() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl
}
