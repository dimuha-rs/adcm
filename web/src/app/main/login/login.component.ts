// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { filter } from 'rxjs/operators';

import { AuthService } from '@app/core';
import { BaseDirective } from '@app/shared';
import { clearProfile } from '@app/core/store';
import { authLogin, authLogout, AuthState, getAuthState } from '@app/core/auth/auth.store';
import { AuthCredentials } from 'adwp_ui';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent extends BaseDirective implements OnInit, OnDestroy {

  message: string;
  checkGL$: Observable<any>;

  constructor(
    private authService: AuthService,
    private router: Router,
    private store: Store<AuthState>,
    private route: ActivatedRoute,
  ) {
    super();
  }

  ngOnInit() {
    this.checkGL$ = this.authService.checkGoogle();
    this.store.dispatch(authLogout());

    const a$ = this.store
      .select(getAuthState)
      .pipe(this.takeUntil())
      .subscribe(state => {
        if (state.isValid) {
          a$.unsubscribe();
          const redirectUrl = this.authService.redirectUrl;
          this.router.navigateByUrl(redirectUrl && redirectUrl !== 'login' && redirectUrl !== '/504' ? redirectUrl : '/admin');
        } else {
          this.store.dispatch(clearProfile());
          this.message = state.message;
        }
      });

    this.route.queryParams
      .pipe(
        filter(p => p['error_code'] === 'AUTH_ERROR'),
        this.takeUntil()
      )
      .subscribe(p => (this.message = p['error_msg']));
  }

  auth(credentials: AuthCredentials) {
    this.store.dispatch(authLogin(credentials));
  }

}
